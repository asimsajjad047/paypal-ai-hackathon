"""
Fetch NEW part prices from Channel3 (UK shops, GBP).

What we learned from explore_channel3.py:
  * client.products.search() returns a pager; .items is the first page of products
  * each product has .offers: one per shop, with .price.price / .price.currency,
    .domain (the shop), .url, .availability and .condition ("new"/"used")
  * country="GB", currency="GBP" gives UK shops in pounds

Run on its own to try one part:   python fetch_channel3.py "RTX 4070"
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
    return Channel3(api_key=config.CHANNEL3_API_KEY, country="GB", currency="GBP")


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
            })
    return offers


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
    for o in search_part(test_part):
        print(f"£{o['price']:>8.2f}  {o['seller']:<25} {o['title'][:60]}")
