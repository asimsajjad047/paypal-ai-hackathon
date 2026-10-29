"""
Optional bulk price collector: fetch Channel3 (new) and eBay (used) prices for
EVERY part, save them, then check price watches.

You don't need this for the app: live_prices.py already fetches real prices for
the parts in a build each time someone asks for one. Running this costs one
Channel3 credit per part, so only use it if you want every part pre-loaded.

Run by hand:            python collect_prices.py
Sources with no API key are skipped, so this is safe to run anywhere.
"""
import config
import fetch_channel3
import fetch_ebay
import watcher


def main():
    if config.CHANNEL3_API_KEY:
        print("== Channel3 (new parts) ==")
        print(f"saved {fetch_channel3.fetch_all()} offers")
    else:
        print("Channel3 skipped (no CHANNEL3_API_KEY)")

    if config.EBAY_CLIENT_ID and config.EBAY_CLIENT_SECRET:
        print("== eBay UK (used parts) ==")
        print(f"saved {fetch_ebay.fetch_all()} offers")
    else:
        print("eBay skipped (no EBAY_CLIENT_ID / EBAY_CLIENT_SECRET)")

    for t in watcher.check_watches():
        print(f"Price watch hit: {t['Name']} at £{t['price']:.2f} -> approve at {t['approval_url']}")


if __name__ == "__main__":
    main()
