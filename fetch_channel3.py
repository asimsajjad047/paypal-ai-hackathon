"""
Fetch NEW part prices from Channel3 (UK shops, GBP).

What we learned from explore_channel3.py:
  * client.products.search() returns a pager; .items is the first page of products
  * each product has .offers: one per shop, with .price.price / .price.currency,
    .domain (the shop), .url, .availability and .condition ("new"/"used")
  * country="GB", currency="GBP" gives UK shops in pounds

Run on its own to try one part:   python fetch_channel3.py "RTX 4070"
(prints the offers, then the live 90-day price history of the first match)
"""
import sys
import time

import config
from listings import matches_part, sane_price

CATEGORY_WORDS = {"CPU": "processor", "GPU": "graphics card", "Motherboard": "motherboard",
                  "RAM": "memory", "PSU": "power supply", "Case": "pc case",
                  "Cooler": "cpu cooler", "Storage": "ssd"}


def _client():
    from channel3_sdk import Channel3     # imported here so the app runs without the SDK
    # pass the key explicitly: the SDK reads env vars at import time, before load_dotenv()
    return Channel3(api_key=config.CHANNEL3_API_KEY, country="GB", currency="GBP",
                    timeout=20)               # a slow shop search must not freeze the app


def search_part(part, limit=20, client=None):
    """part = {"Name", "Brand", "Category", "RefPrice"} -> list of normalised offers."""
    if not config.CHANNEL3_API_KEY:
        return []
    client = client or _client()
    query = f"{part['Brand']} {part['Name']} {CATEGORY_WORDS.get(part['Category'], '')}".strip()
    try:
        page = client.products.search(query=query, limit=limit)
    except Exception as e:                       # network/API problems: skip this part
        print(f"  Channel3 error for {part['Name']}: {e}")
        return []

    offers = []
    for product in page.items or []:
        if not matches_part(product.title, part["Name"], part["Brand"]):
            continue
        for offer in product.offers or []:
            price = offer.price.price
            if offer.price.currency != "GBP" or not sane_price(price, part["RefPrice"]):
                continue
            if str(offer.availability) == "OutOfStock":
                continue
            offers.append({
                "source": "channel3",
                "external_id": f"{product.id}:{offer.domain}",
                "title": product.title,
                "price": round(price, 2),
                "currency": "GBP",
                "condition": "Used" if str(offer.condition).lower() == "used" else "New",
                "seller": offer.domain,
                "url": offer.url,
                "product_id": product.id,         # needed to ask for price history
            })
    return offers


def price_history(product_id, client=None, days=90):
    """
    LIVE price history for one product, straight from Channel3 (not our database).
    GET /v0/price-tracking/history/{product_id}?days=90 gives:
      history     one point per price change: timestamp, price, currency
      statistics  min/max/mean and current_status: "low", "typical" or "high"
    Returns {"history": [{"Date", "Price"}], "status", "low", "high"} or None.
    """
    if not config.CHANNEL3_API_KEY or not product_id:
        return None
    client = client or _client()
    try:
        r = client.price_tracking.retrieve_history(product_id, days=days)
    except Exception as e:
        print(f"  Channel3 history error for {product_id}: {e}")
        return None
    # several points on one day -> keep that day's lowest price (same as PriceHistory)
    by_day = {}
    for point in r.history or []:
        if point.currency != "GBP":
            continue
        day = point.timestamp.date().isoformat()
        by_day[day] = min(point.price, by_day.get(day, point.price))
    stats = r.statistics
    return {"history": [{"Date": d, "Price": round(p, 2)} for d, p in sorted(by_day.items())],
            "status": str(stats.current_status) if stats else None,
            "low": stats.min_price if stats else None,
            "high": stats.max_price if stats else None}


def fetch_all(save=True, pause=1.0):
    """Search every part in the database and save matching offers."""
    from listings import parts_to_track, save_listings
    client = _client()
    total = 0
    for part in parts_to_track():
        offers = search_part(part, client=client)
        print(f"{part['Name']:<28} {len(offers)} offers")
        if save and offers:
            total += save_listings(part["PartID"], offers)
        time.sleep(pause)                        # be polite: stay under the rate limit
    return total


if __name__ == "__main__":
    if not config.CHANNEL3_API_KEY:
        sys.exit("Set CHANNEL3_API_KEY in .env first")
    name = sys.argv[1] if len(sys.argv) > 1 else "RTX 4070"
    test_part = {"Name": name, "Brand": "", "Category": "GPU", "RefPrice": 500}
    found = search_part(test_part)
    for o in found:
        print(f"£{o['price']:>8.2f}  {o['seller']:<25} {o['title'][:60]}")
    if found:
        h = price_history(found[0]["product_id"])
        if h:
            print(f"\n{len(h['history'])} days of history, today's price is {h['status']} "
                  f"(90-day low £{h['low']}, high £{h['high']})")
