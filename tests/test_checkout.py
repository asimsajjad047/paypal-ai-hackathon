import checkout
import config
import paypal_client
import watcher
from agent import design_build
from db import get_connection


def _build_with_used_part():
    r = design_build(1100, "both", ["Valorant", "Cyberpunk 2077"], explain=False)
    assert any(p["Condition"] == "Used" for p in r["build"]["parts"].values())
    return r


def test_mock_checkout_pays_shops_and_holds_used_parts():
    r = _build_with_used_part()
    used = next(p for p in r["build"]["parts"].values() if p["Condition"] == "Used")
    order = checkout.create_checkout(r["build"], r["details"], {used["ListingID"]: used["Price"] - 5})
    assert order["mode"] == "mock" and "token=" in order["approval_url"]
    assert order["total"] == round(r["build"]["total"] - 5, 2)

    summary = checkout.capture_checkout(order["order_id"])
    assert summary["order"]["Status"] == "COMPLETED"
    statuses = {p["Seller"]: p["Status"] for p in summary["payments"]}
    assert statuses[used["Seller"]] == "Held"
    assert all(s == "Paid" for name, s in statuses.items() if name != used["Seller"])

    # capturing again (page refresh) changes nothing
    assert checkout.capture_checkout(order["order_id"])["payments"] == summary["payments"]

    held = next(p for p in summary["payments"] if p["Status"] == "Held")
    checkout.report_problem(held["PaymentID"])
    after = checkout.order_summary(order["order_id"])
    assert next(p for p in after["payments"] if p["PaymentID"] == held["PaymentID"])["Status"] == "Refunded"


def test_cancel_marks_build_cancelled():
    r = _build_with_used_part()
    order = checkout.create_checkout(r["build"], r["details"])
    checkout.cancel_checkout(order["order_id"])
    conn = get_connection()
    status = conn.execute("SELECT Status FROM Build WHERE BuildID = ?", (order["build_id"],)).fetchone()[0]
    conn.close()
    assert status == "Cancelled"


class FakeSandbox(paypal_client.MockPayPal):
    """Pretends to be real PayPal so we can inspect what we would send."""
    mode_name = "sandbox"

    def create_order(self, purchase_units, return_url, cancel_url, request_id=None):
        self.sent = purchase_units
        return super().create_order(purchase_units, return_url, cancel_url, request_id)


def test_split_mode_has_one_purchase_unit_per_seller(monkeypatch):
    monkeypatch.setattr(config, "PAYPAL_CHECKOUT_MODE", "split")
    r = _build_with_used_part()
    fake = FakeSandbox()
    checkout.create_checkout(r["build"], r["details"], client=fake)
    sellers = {p["SellerID"] for p in r["build"]["parts"].values()}
    assert len(fake.sent) == len(sellers)
    for unit in fake.sent:
        assert "@" in unit["payee"]["email_address"]
        items = sum(float(i["unit_amount"]["value"]) for i in unit["items"])
        assert abs(items - float(unit["amount"]["value"])) < 0.001   # PayPal rejects mismatches


def test_approval_link_is_found():
    order = {"links": [{"rel": "self", "href": "a"}, {"rel": "payer-action", "href": "b"}]}
    assert paypal_client.approval_link(order) == "b"


def test_price_watch_creates_order_when_target_hit():
    watcher.add_watch(part_id=15, target_price=200, max_price=200)   # Ryzen 5 5600, £99
    watcher.add_watch(part_id=7, target_price=100, max_price=100)    # RTX 4070, £539: no
    hits = watcher.check_watches()
    assert [h["PartID"] for h in hits] == [15]
    assert hits[0]["approval_url"]
