"""
Live prices: fetched the moment someone asks for a build, not by a daily job.

  1. Pick a build from what we already know (test prices to start with).
  2. For each picked part, all at the same time (one thread per part):
       Channel3 -> real NEW offers from UK shops + the LIVE 90-day price history
       eBay     -> real USED listings (only if the user allows used parts)
  3. Save those offers, then pick again. The picker prefers real listings seen
     today, so the real prices (and real "View listing" links) win.
  4. If the new pick has parts we haven't looked up yet, look those up too.
     MAX_ROUNDS stops this from searching forever (each search costs a credit).

With no keys (or RIGAGENT_OFFLINE_PRICES=true) this does nothing, and the
app uses the test prices, same as before.
"""
from concurrent.futures import ThreadPoolExecutor

import config
import fetch_channel3
import fetch_ebay
from db import get_connection
from listings import save_history, save_listings
from picker import pick_build

MAX_ROUNDS = 2


def enabled():
    has_source = config.CHANNEL3_API_KEY or (config.EBAY_CLIENT_ID and config.EBAY_CLIENT_SECRET)
    return config.LIVE_PRICES and bool(has_source)


def _part_info(part_ids):
    """Name, brand and category for the search, and a reference price to reject silly prices."""
    conn = get_connection()
    try:
        rows = conn.execute(f"""
            SELECT p.PartID, p.Name, p.Brand, p.Category,
                   COALESCE(MIN(CASE WHEN l.Source = 'test' THEN l.Price END), MIN(l.Price)) AS RefPrice
            FROM Part p JOIN Listing l ON l.PartID = p.PartID
            WHERE p.PartID IN ({','.join('?' * len(part_ids))})
            GROUP BY p.PartID""", part_ids).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _lookup(part, allow_used, client):
    """Ask every source about one part. Runs in a thread, so it must not write to the database."""
    offers = fetch_channel3.search_part(part, client=client)
    history = None
    new = [o for o in offers if o["condition"] == "New"]
    if new:
        cheapest = min(new, key=lambda o: o["price"])
        history = fetch_channel3.price_history(cheapest["product_id"], client=client)
    if allow_used:
        offers = offers + fetch_ebay.search_part(part)
    return offers, history


def refresh(part_ids, allow_used):
    """
    Look up these parts live and save what we find.
    Returns {PartID: {"offers": how many real offers, "status": "low"/"typical"/"high" or None}}
    """
    parts = _part_info(part_ids)
    client = fetch_channel3._client() if config.CHANNEL3_API_KEY else None
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = list(pool.map(lambda p: _lookup(p, allow_used, client), parts))

    summary = {}
    for part, (offers, history) in zip(parts, found):      # database writes: one at a time
        if history and history["history"]:
            save_history(part["PartID"], history["history"], "New", "channel3")
        if offers:
            save_listings(part["PartID"], offers)
        summary[part["PartID"]] = {"offers": len(offers), "status": history and history["status"]}
    return summary


def pick(budget, requirements):
    """
    Same as picker.pick_build, but with live prices for the parts it picks.
    Returns (build or None, message, live) where live = {"parts_checked", "real_parts", "sources"}
    or None when live prices are off.
    """
    build, message = pick_build(budget, requirements)
    if build is None or not enabled():
        return build, message, None

    checked = {}
    for _ in range(MAX_ROUNDS):
        todo = [p["PartID"] for p in build["parts"].values() if p["PartID"] not in checked]
        if not todo:
            break
        checked.update(refresh(todo, requirements["allow_used"]))
        build, message = pick_build(budget, requirements)
        if build is None:            # real prices pushed every option over budget
            return None, message + " (using live prices)", {"parts_checked": len(checked),
                                                             "real_parts": 0, "sources": []}

    for part in build["parts"].values():                 # Channel3's verdict, for buy/wait
        part["PriceStatus"] = checked.get(part["PartID"], {}).get("status")
    real = [p for p in build["parts"].values() if p["Source"] != "test"]
    return build, message, {"parts_checked": len(checked), "real_parts": len(real),
                            "sources": sorted({p["Source"] for p in real})}
