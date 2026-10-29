"""
Fetch USED part prices from eBay UK with the Browse API.

Two steps (same idea as PayPal):
  1. POST /identity/v1/oauth2/token with App ID + Cert ID  -> application token
  2. GET  /buy/browse/v1/item_summary/search?q=...         -> listings
     header X-EBAY-C-MARKETPLACE-ID: EBAY_GB  (UK site, prices in GBP)
     filter conditionIds:{3000} = "Used"

Run on its own to try one part:   python fetch_ebay.py "RTX 3060"
"""
import base64
import sys
import time

import requests

import config
from listings import matches_part, sane_price

_token = {"value": None, "expires": 0}


def get_token():
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    creds = base64.b64encode(f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}".encode()).decode()
    r = requests.post(f"{config.EBAY_BASE_URL}/identity/v1/oauth2/token",
                      headers={"Authorization": f"Basic {creds}",
                               "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "client_credentials",
                            "scope": "https://api.ebay.com/oauth/api_scope"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    _token.update(value=data["access_token"], expires=time.time() + data.get("expires_in", 7200))
    return _token["value"]


def search_part(part, limit=20):
    """part = {"Name", "Brand", "RefPrice"} -> list of normalised USED offers."""
    if not (config.EBAY_CLIENT_ID and config.EBAY_CLIENT_SECRET):
        return []
    low, high = part["RefPrice"] * 0.35, part["RefPrice"] * 1.2
    try:
        r = requests.get(
            f"{config.EBAY_BASE_URL}/buy/browse/v1/item_summary/search",
            headers={"Authorization": f"Bearer {get_token()}",
                     "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB"},
            params={"q": f"{part['Brand']} {part['Name']}".strip(),
                    "filter": f"conditionIds:{{3000}},buyingOptions:{{FIXED_PRICE}},"
                              f"price:[{low:.0f}..{high:.0f}],priceCurrency:GBP",
                    "limit": limit},
            timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  eBay error for {part['Name']}: {e}")
        return []

    offers = []
    for item in r.json().get("itemSummaries", []):
        price = float(item.get("price", {}).get("value", 0))
        if item.get("price", {}).get("currency") != "GBP":
            continue
        if not matches_part(item.get("title", ""), part["Name"]) or not sane_price(price, part["RefPrice"]):
            continue
        offers.append({
            "source": "ebay",
            "external_id": item["itemId"],
            "title": item["title"],
            "price": price,
            "currency": "GBP",
            "condition": "Used",
            "seller": f"{item.get('seller', {}).get('username', 'ebay seller')} (eBay)",
            "url": item.get("itemWebUrl"),
        })
    return offers


def fetch_all(save=True, pause=1.0):
    from listings import parts_to_track, save_listings
    total = 0
    for part in parts_to_track():
        offers = search_part(part)
        print(f"{part['Name']:<28} {len(offers)} used offers")
        if save and offers:
            total += save_listings(part["PartID"], offers)
        time.sleep(pause)
    return total


if __name__ == "__main__":
    if not (config.EBAY_CLIENT_ID and config.EBAY_CLIENT_SECRET):
        sys.exit("Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET in .env first")
    name = sys.argv[1] if len(sys.argv) > 1 else "RTX 3060"
    for o in search_part({"Name": name, "Brand": "", "RefPrice": 250}):
        print(f"£{o['price']:>8.2f}  {o['seller']:<25} {o['title'][:60]}")
