"""
Price watch ("auto-buy") for parts rated Wait.

The user sets a target price and a pre-approved maximum. When the cheapest
listing drops to the target, RigAgent creates the PayPal order straight away,
so buying is a single tap.

Honest limit: PayPal (rightly) still asks the buyer to approve every payment.
Charging with no click at all would need a saved payment method (PayPal Vault),
which is the next step after the hackathon.
"""
import checkout
from db import get_connection
from picker import get_options


def add_watch(part_id, target_price, max_price=None, allow_used=False):
    max_price = max(max_price or target_price, target_price)
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO Watch (PartID, TargetPrice, MaxPrice, AllowUsed) VALUES (?, ?, ?, ?)",
                           (part_id, target_price, max_price, int(allow_used)))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_watches():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT w.*, p.Name, p.Category FROM Watch w JOIN Part p ON p.PartID = w.PartID "
                            "ORDER BY w.WatchID DESC").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def cancel_watch(watch_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE Watch SET Status = 'Cancelled' WHERE WatchID = ? AND Status = 'Watching'", (watch_id,))
        conn.commit()
    finally:
        conn.close()


def _cheapest(part_id, allow_used):
    for items in get_options(allow_used).values():
        for item in items:
            if item["PartID"] == part_id:
                return item
    return None


def check_watches(client=None):
    """Run by collect_prices.py after fetching prices (or from the app). Returns triggered watches."""
    triggered = []
    for w in list_watches():
        if w["Status"] != "Watching":
            continue
        best = _cheapest(w["PartID"], bool(w["AllowUsed"]))
        if best is None or best["Price"] > w["TargetPrice"] or best["Price"] > w["MaxPrice"]:
            continue
        build = {"platform": "Price watch", "parts": {w["Category"]: best}, "upgrades": [],
                 "total": best["Price"]}
        details = {"summary": f"price watch on {w['Name']} (target £{w['TargetPrice']:.0f})",
                   "budget": w["MaxPrice"]}
        order = checkout.create_checkout(build, details, client=client)
        conn = get_connection()
        try:
            conn.execute("UPDATE Watch SET Status = 'Triggered', OrderID = ? WHERE WatchID = ?",
                         (order["order_id"], w["WatchID"]))
            conn.commit()
        finally:
            conn.close()
        triggered.append({**w, "price": best["Price"], "approval_url": order["approval_url"],
                          "order_id": order["order_id"]})
    return triggered
