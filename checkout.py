"""
Checkout: turns an approved build into ONE PayPal payment that pays every seller.

Two ways to do it (set PAYPAL_CHECKOUT_MODE in .env):

  marketplace (default)
      The buyer pays RigAgent once. RigAgent then pays each SHOP straight away with
      PayPal Payouts, and HOLDS the money for USED parts (escrow) until the buyer
      confirms the part arrived and works. A problem -> partial refund to the buyer.
      This is how real marketplaces protect both sides.

  split
      One PayPal order with one purchase unit per seller, each with that seller's
      email as payee, so PayPal pays every seller directly in the same checkout.
      (PayPal lists this as a platform feature; if your sandbox app isn't allowed
      to use it, PayPal returns an error and you can switch back to marketplace.)

Without PayPal keys everything runs against MockPayPal and is labelled "mock".

Safety rule: nothing is charged until the user presses Approve AND approves on
PayPal's own page. RigAgent can never pay on its own.
"""
import json
import uuid

import config
import paypal_client
from db import get_connection


def _money(x):
    return f"{x:.2f}"


def _purchase_unit(reference_id, description, lines, currency, payee_email=None):
    """lines = [{"name", "price", "seller"}] -> one PayPal purchase unit."""
    item_total = round(sum(round(l["price"], 2) for l in lines), 2)
    unit = {
        "reference_id": reference_id,
        "description": description[:127],
        "amount": {"currency_code": currency, "value": _money(item_total),
                   "breakdown": {"item_total": {"currency_code": currency, "value": _money(item_total)}}},
        "items": [{"name": l["name"][:127], "quantity": "1", "category": "PHYSICAL_GOODS",
                   "description": f"{l['condition']} - sold by {l['seller']}"[:127],
                   "unit_amount": {"currency_code": currency, "value": _money(round(l["price"], 2))}}
                  for l in lines],
    }
    if payee_email:
        unit["payee"] = {"email_address": payee_email}
    return unit


def _sellers_for(listing_ids):
    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT l.ListingID, s.SellerID, s.Name, s.PayPalEmail, s.SellerType "
            f"FROM Listing l JOIN Seller s ON s.SellerID = l.SellerID "
            f"WHERE l.ListingID IN ({','.join('?' * len(listing_ids))})", listing_ids).fetchall()
    finally:
        conn.close()
    return {r["ListingID"]: dict(r) for r in rows}


def save_build(build, details, agreed_prices=None):
    """Store the approved build. agreed_prices = {ListingID: negotiated price}."""
    agreed_prices = agreed_prices or {}
    total = sum(agreed_prices.get(p["ListingID"], p["Price"]) for p in build["parts"].values())
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO Build (BuildName, Budget, Requirements, TotalPrice, Status) "
            "VALUES (?, ?, ?, ?, 'Approved')",
            (f"{build['platform']} build for {details.get('summary', 'gaming')}"[:120],
             details.get("budget"), json.dumps(details, default=str), round(total, 2)))
        build_id = cur.lastrowid
        # the same listing twice (e.g. 2 SSDs) becomes Quantity 2
        counts = {}
        for p in build["parts"].values():
            counts[p["ListingID"]] = counts.get(p["ListingID"], 0) + 1
        for listing_id, qty in counts.items():
            conn.execute("INSERT INTO BuildItem (BuildID, ListingID, Quantity, AgreedPrice) VALUES (?, ?, ?, ?)",
                         (build_id, listing_id, qty, agreed_prices.get(listing_id)))
        conn.commit()
    finally:
        conn.close()
    return build_id, round(total, 2)


def create_checkout(build, details, agreed_prices=None, client=None):
    """
    Save the build, create the PayPal order, and return the link the buyer must open.
    Returns {"build_id", "order_id", "approval_url", "mode", "total", "sellers"}.
    """
    client = client or paypal_client.get_client()
    agreed_prices = agreed_prices or {}
    currency = config.PAYPAL_CURRENCY
    build_id, total = save_build(build, details, agreed_prices)

    listing_ids = [p["ListingID"] for p in build["parts"].values()]
    sellers = _sellers_for(listing_ids)

    # Group the parts by seller: each seller is owed the sum of their parts
    by_seller = {}
    for cat, p in build["parts"].items():
        s = sellers[p["ListingID"]]
        entry = by_seller.setdefault(s["SellerID"], {
            "seller": s, "lines": [], "escrow": False})
        entry["lines"].append({"name": f"{cat}: {p['Name']}", "condition": p["Condition"],
                               "seller": s["Name"], "price": agreed_prices.get(p["ListingID"], p["Price"])})
        if p["Condition"] == "Used" or s["SellerType"] == "Individual":
            entry["escrow"] = True

    mode = "mock" if client.mode_name == "mock" else config.PAYPAL_CHECKOUT_MODE
    if mode == "split":
        units = [_purchase_unit(f"seller-{sid}", f"RigAgent parts from {e['seller']['Name']}",
                                e["lines"], currency, payee_email=e["seller"]["PayPalEmail"])
                 for sid, e in by_seller.items()]
    else:   # marketplace or mock: one unit paid to RigAgent, sellers paid afterwards
        all_lines = [l for e in by_seller.values() for l in e["lines"]]
        units = [_purchase_unit(f"build-{build_id}", f"RigAgent PC build #{build_id}",
                                all_lines, currency)]

    order = client.create_order(units,
                                return_url=f"{config.APP_BASE_URL}/?paypal=return",
                                cancel_url=f"{config.APP_BASE_URL}/?paypal=cancel",
                                request_id=f"rigagent-build-{build_id}-{uuid.uuid4().hex[:6]}")

    conn = get_connection()
    try:
        conn.execute("INSERT INTO PayPalOrder (OrderID, BuildID, Mode, Status, Total, Currency, ApprovalURL) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (order["id"], build_id, mode, order["status"], total, currency, order["approval_url"]))
        for sid, e in by_seller.items():
            amount = round(sum(l["price"] for l in e["lines"]), 2)
            escrow = 1 if (e["escrow"] and mode != "split") else 0
            conn.execute("INSERT INTO SellerPayment (OrderID, SellerID, Amount, Escrow, Status) "
                         "VALUES (?, ?, ?, ?, 'Pending')", (order["id"], sid, amount, escrow))
        conn.commit()
    finally:
        conn.close()

    return {"build_id": build_id, "order_id": order["id"], "approval_url": order["approval_url"],
            "mode": mode, "total": total, "currency": currency,
            "sellers": [{"name": e["seller"]["Name"], "amount": round(sum(l["price"] for l in e["lines"]), 2),
                         "escrow": e["escrow"] and mode != "split"} for e in by_seller.values()]}


# ---------- After the buyer approves on PayPal ----------

def _set(conn, sql, *args):
    conn.execute(sql, args)


def capture_checkout(order_id, client=None):
    """
    Called when PayPal sends the buyer back (?paypal=return&token=ORDER_ID).
    Captures the money, then pays shops / holds escrow. Safe to call twice.
    """
    client = client or paypal_client.get_client()
    conn = get_connection()
    try:
        order = conn.execute("SELECT * FROM PayPalOrder WHERE OrderID = ?", (order_id,)).fetchone()
        if order is None:
            raise ValueError(f"Unknown order {order_id}")
        if order["Status"] == "COMPLETED":
            return order_summary(order_id)          # already done (page refreshed)

        result = client.capture_order(order_id)
        status = result.get("status", "UNKNOWN")
        _set(conn, "UPDATE PayPalOrder SET Status = ?, DateUpdated = datetime('now') WHERE OrderID = ?",
             status, order_id)
        if status != "COMPLETED":
            conn.commit()
            return order_summary(order_id)

        payments = conn.execute("SELECT p.*, s.Name, s.PayPalEmail FROM SellerPayment p "
                                "JOIN Seller s ON s.SellerID = p.SellerID WHERE OrderID = ?",
                                (order_id,)).fetchall()
        units = result.get("purchase_units", [])

        if order["Mode"] == "split":
            # every seller was paid directly by PayPal: record each capture
            captures = {u.get("reference_id"): u["payments"]["captures"][0]["id"]
                        for u in units if u.get("payments", {}).get("captures")}
            for i, p in enumerate(payments):
                cap = captures.get(f"seller-{p['SellerID']}") or \
                    (units[i]["payments"]["captures"][0]["id"] if i < len(units) else None)
                _set(conn, "UPDATE SellerPayment SET Status = 'Paid', PayPalRef = ?, "
                     "Note = 'Paid directly by PayPal at checkout' WHERE PaymentID = ?", cap, p["PaymentID"])
        else:
            capture_id = units[0]["payments"]["captures"][0]["id"]
            _set(conn, "UPDATE PayPalOrder SET CaptureID = ? WHERE OrderID = ?", capture_id, order_id)
            shops = [p for p in payments if not p["Escrow"]]
            for p in payments:
                if p["Escrow"]:
                    _set(conn, "UPDATE SellerPayment SET Status = 'Held', "
                         "Note = 'Held in escrow until you confirm delivery' WHERE PaymentID = ?", p["PaymentID"])
            if shops:
                try:
                    payout = client.payout(f"{order_id}-shops",
                                           [{"email": p["PayPalEmail"], "amount": p["Amount"],
                                             "ref": f"pay-{p['PaymentID']}",
                                             "note": f"RigAgent order {order_id}"} for p in shops],
                                           order["Currency"])
                    for p in shops:
                        _set(conn, "UPDATE SellerPayment SET Status = 'Paid', PayPalRef = ?, "
                             "Note = 'Paid out by RigAgent' WHERE PaymentID = ?", payout["batch_id"], p["PaymentID"])
                except paypal_client.PayPalError as e:
                    for p in shops:
                        _set(conn, "UPDATE SellerPayment SET Status = 'Failed', Note = ? WHERE PaymentID = ?",
                             f"Payout failed: {e}"[:250], p["PaymentID"])

        _set(conn, "UPDATE Build SET Status = 'Paid' WHERE BuildID = ?", order["BuildID"])
        conn.commit()
    finally:
        conn.close()
    return order_summary(order_id)


def cancel_checkout(order_id):
    """Buyer pressed Cancel on PayPal's page."""
    conn = get_connection()
    try:
        order = conn.execute("SELECT BuildID, Status FROM PayPalOrder WHERE OrderID = ?", (order_id,)).fetchone()
        if order and order["Status"] != "COMPLETED":
            conn.execute("UPDATE PayPalOrder SET Status = 'CANCELLED' WHERE OrderID = ?", (order_id,))
            conn.execute("UPDATE Build SET Status = 'Cancelled' WHERE BuildID = ?", (order["BuildID"],))
            conn.commit()
    finally:
        conn.close()


# ---------- Escrow: release or refund used-part money ----------

def _escrow_payment(conn, payment_id):
    p = conn.execute("SELECT p.*, s.Name, s.PayPalEmail, o.CaptureID, o.Currency, o.Mode "
                     "FROM SellerPayment p JOIN Seller s ON s.SellerID = p.SellerID "
                     "JOIN PayPalOrder o ON o.OrderID = p.OrderID WHERE PaymentID = ?",
                     (payment_id,)).fetchone()
    if p is None or p["Status"] != "Held":
        raise ValueError("This payment isn't being held in escrow")
    return p


def confirm_delivery(payment_id, client=None):
    """Buyer says the used part arrived and works -> pay the seller."""
    client = client or paypal_client.get_client()
    conn = get_connection()
    try:
        p = _escrow_payment(conn, payment_id)
        payout = client.payout(f"{p['OrderID']}-escrow-{payment_id}",
                               [{"email": p["PayPalEmail"], "amount": p["Amount"],
                                 "ref": f"pay-{payment_id}", "note": "Escrow released by buyer"}],
                               p["Currency"])
        conn.execute("UPDATE SellerPayment SET Status = 'Paid', PayPalRef = ?, "
                     "Note = 'Escrow released: buyer confirmed delivery' WHERE PaymentID = ?",
                     (payout["batch_id"], payment_id))
        conn.commit()
    finally:
        conn.close()
    return payout


def report_problem(payment_id, reason="Item not as described", client=None):
    """Buyer reports a problem with a used part -> refund that part of the payment."""
    client = client or paypal_client.get_client()
    conn = get_connection()
    try:
        p = _escrow_payment(conn, payment_id)
        refund = client.refund_capture(p["CaptureID"], p["Amount"], p["Currency"], reason)
        conn.execute("UPDATE SellerPayment SET Status = 'Refunded', PayPalRef = ?, Note = ? WHERE PaymentID = ?",
                     (refund.get("id"), f"Refunded to buyer: {reason}"[:250], payment_id))
        conn.commit()
    finally:
        conn.close()
    return refund


def refresh_status(order_id, client=None):
    """Ask PayPal for the latest order status (order tracking)."""
    client = client or paypal_client.get_client()
    status = client.get_order(order_id).get("status", "UNKNOWN")
    conn = get_connection()
    try:
        conn.execute("UPDATE PayPalOrder SET Status = ?, DateUpdated = datetime('now') "
                     "WHERE OrderID = ? AND Status != 'COMPLETED'", (status, order_id))
        conn.commit()
    finally:
        conn.close()
    return order_summary(order_id)


def order_summary(order_id):
    conn = get_connection()
    try:
        order = conn.execute("SELECT * FROM PayPalOrder WHERE OrderID = ?", (order_id,)).fetchone()
        if order is None:
            return None
        payments = conn.execute("SELECT p.PaymentID, s.Name AS Seller, p.Amount, p.Escrow, p.Status, "
                                "p.PayPalRef, p.Note FROM SellerPayment p JOIN Seller s ON s.SellerID = p.SellerID "
                                "WHERE p.OrderID = ? ORDER BY p.PaymentID", (order_id,)).fetchall()
        items = conn.execute("SELECT p.Category, p.Name, COALESCE(bi.AgreedPrice, l.Price) AS Price, "
                             "l.Condition, s.Name AS Seller FROM BuildItem bi "
                             "JOIN Listing l ON l.ListingID = bi.ListingID JOIN Part p ON p.PartID = l.PartID "
                             "JOIN Seller s ON s.SellerID = l.SellerID WHERE bi.BuildID = ?",
                             (order["BuildID"],)).fetchall()
    finally:
        conn.close()
    return {"order": dict(order), "payments": [dict(p) for p in payments], "items": [dict(i) for i in items]}


def list_orders(limit=20):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT OrderID, BuildID, Mode, Status, Total, Currency, DateCreated "
                            "FROM PayPalOrder ORDER BY DateCreated DESC LIMIT ?", (limit,)).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
