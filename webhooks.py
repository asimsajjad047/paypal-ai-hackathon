"""
PayPal webhooks: PayPal tells RigAgent when something happens to a payment,
even if the buyer closed the browser before coming back to the app.

PayPal POSTs JSON to  <APP_BASE_URL>/paypal/webhook  (see server.py). We:
  1. check the signature with PayPal (so nobody can fake "payment completed")
  2. ignore events we've already seen (PayPal may send the same one twice)
  3. update the database

Events handled:
  CHECKOUT.ORDER.APPROVED        buyer approved but never came back -> capture now
  PAYMENT.CAPTURE.COMPLETED      money arrived
  PAYMENT.CAPTURE.DENIED/REVERSED/REFUNDED   money failed, clawed back or refunded
  PAYMENT.PAYOUTS-ITEM.*         a seller payout succeeded / failed / unclaimed
"""
import json
import sqlite3

import checkout
import config
import paypal_client
from db import get_connection


def _order_id_from_capture(resource):
    return resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")


def _set_order_status(order_id, status):
    conn = get_connection()
    try:
        conn.execute("UPDATE PayPalOrder SET Status = ?, DateUpdated = datetime('now') WHERE OrderID = ?",
                     (status, order_id))
        conn.commit()
    finally:
        conn.close()


def _payout_item(resource, status, note):
    """sender_item_id is "pay-<PaymentID>" (set in checkout.py), which links back to our row."""
    ref = resource.get("payout_item", {}).get("sender_item_id", "")
    if not ref.startswith("pay-"):
        return "not a RigAgent payout"
    conn = get_connection()
    try:
        conn.execute("UPDATE SellerPayment SET Status = ?, Note = ? WHERE PaymentID = ?",
                     (status, note, int(ref[4:])))
        conn.commit()
    finally:
        conn.close()
    return f"seller payment {ref[4:]} -> {status}"


def handle_event(event, client=None):
    """Update the database for one (already verified) event. Returns what we did."""
    kind = event.get("event_type", "")
    res = event.get("resource", {})

    conn = get_connection()
    try:
        conn.execute("INSERT INTO WebhookEvent (EventID, EventType, ResourceID, Summary) VALUES (?, ?, ?, ?)",
                     (event.get("id"), kind, res.get("id"), (event.get("summary") or "")[:250]))
        conn.commit()
    except sqlite3.IntegrityError:
        return "duplicate, ignored"          # we've already handled this event ID
    finally:
        conn.close()

    if kind == "CHECKOUT.ORDER.APPROVED":
        summary = checkout.order_summary(res.get("id"))
        if summary is None:
            handled = "unknown order"
        elif summary["order"]["Status"] == "COMPLETED":
            handled = "already captured"
        else:
            checkout.capture_checkout(res["id"], client)
            handled = "captured (buyer didn't return to the app)"
    elif kind == "PAYMENT.CAPTURE.COMPLETED":
        order_id = _order_id_from_capture(res)
        handled = f"order {order_id} confirmed paid" if order_id else "no order id"
    elif kind in ("PAYMENT.CAPTURE.DENIED", "PAYMENT.CAPTURE.REVERSED"):
        order_id = _order_id_from_capture(res)
        if order_id:
            _set_order_status(order_id, kind.rsplit(".", 1)[1])
        handled = f"order {order_id} marked {kind.rsplit('.', 1)[1]}"
    elif kind == "PAYMENT.CAPTURE.REFUNDED":
        handled = "refund confirmed by PayPal"
    elif kind == "PAYMENT.PAYOUTS-ITEM.SUCCEEDED":
        handled = _payout_item(res, "Paid", "Payout confirmed by PayPal")
    elif kind in ("PAYMENT.PAYOUTS-ITEM.FAILED", "PAYMENT.PAYOUTS-ITEM.RETURNED",
                  "PAYMENT.PAYOUTS-ITEM.BLOCKED", "PAYMENT.PAYOUTS-ITEM.UNCLAIMED"):
        handled = _payout_item(res, "Failed", f"Payout {kind.rsplit('.', 1)[1].lower()} (PayPal webhook)")
    else:
        handled = "not used by RigAgent"

    conn = get_connection()
    try:
        conn.execute("UPDATE WebhookEvent SET Handled = ? WHERE EventID = ?", (handled, event.get("id")))
        conn.commit()
    finally:
        conn.close()
    return handled


def receive(headers, raw_body, client=None):
    """
    Entry point for the web route. Returns (http_status, message).
    headers: dict with lower-case keys.
    """
    if not (config.PAYPAL_ENABLED and config.PAYPAL_WEBHOOK_ID):
        return 503, "Webhooks not configured (set PAYPAL_WEBHOOK_ID)"
    try:
        event = json.loads(raw_body)
    except ValueError:
        return 400, "Not JSON"
    client = client or paypal_client.get_client()
    try:
        if not client.verify_webhook(headers, event, config.PAYPAL_WEBHOOK_ID):
            return 400, "Signature check failed"
    except paypal_client.PayPalError as e:
        return 502, f"Couldn't verify with PayPal: {e}"
    return 200, handle_event(event, client)


def recent_events(limit=20):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT EventType, ResourceID, Handled, Received FROM WebhookEvent "
                            "ORDER BY Received DESC LIMIT ?", (limit,)).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
