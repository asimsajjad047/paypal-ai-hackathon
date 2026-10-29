import checkout
import config
import webhooks
from agent import alternatives, design_build, swap_part
from db import get_connection


def _order():
    r = design_build(1100, "both", ["Valorant"], explain=False)
    return checkout.create_checkout(r["build"], r["details"])


def test_approved_webhook_captures_when_buyer_never_returns():
    order = _order()
    event = {"id": "WH-1", "event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": order["order_id"]}}
    assert "captured" in webhooks.handle_event(event)
    assert checkout.order_summary(order["order_id"])["order"]["Status"] == "COMPLETED"
    assert webhooks.handle_event(event) == "duplicate, ignored"     # PayPal retries are harmless


def test_payout_failure_webhook_marks_seller_payment():
    order = _order()
    summary = checkout.capture_checkout(order["order_id"])
    paid = next(p for p in summary["payments"] if p["Status"] == "Paid")
    event = {"id": "WH-2", "event_type": "PAYMENT.PAYOUTS-ITEM.UNCLAIMED",
             "resource": {"payout_item": {"sender_item_id": f"pay-{paid['PaymentID']}"}}}
    webhooks.handle_event(event)
    conn = get_connection()
    status = conn.execute("SELECT Status FROM SellerPayment WHERE PaymentID = ?", (paid["PaymentID"],)).fetchone()[0]
    conn.close()
    assert status == "Failed"


def test_unverified_webhooks_are_refused(monkeypatch):
    assert webhooks.receive({}, b"{}")[0] == 503                 # not configured
    monkeypatch.setattr(config, "PAYPAL_ENABLED", True)
    monkeypatch.setattr(config, "PAYPAL_WEBHOOK_ID", "WH-ID")

    class Forged:
        def verify_webhook(self, headers, event, webhook_id):
            return False
    assert webhooks.receive({}, b'{"id": "x"}', client=Forged())[0] == 400


def test_ram_and_storage_choices_win():
    r = design_build(1100, "new", ["Fortnite"], min_ram_gb=64, min_storage_gb=2000, explain=False)
    assert r["build"]["parts"]["RAM"]["Capacity_GB"] >= 64
    assert r["build"]["parts"]["Storage"]["Capacity_GB"] >= 2000


def test_swap_only_offers_compatible_parts_and_rechecks():
    r = design_build(1100, "new", ["Fortnite"], explain=False)
    alts = alternatives(r, "Case")
    assert alts and all(a["Name"] != "NR200P" for a in alts)     # Mini-ITX case can't fit
    new = swap_part(r, "Case", alts[0], explain=False)
    assert new["build"]["parts"]["Case"]["PartID"] == alts[0]["PartID"]
    assert all(c["passed"] for c in new["checks"])
    assert r["build"]["parts"]["Case"]["PartID"] != alts[0]["PartID"]   # original untouched
