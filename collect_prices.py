"""
Daily price collector: fetch Channel3 (new) and eBay (used) prices for every
part, save them, then check price watches.

Run by hand:            python collect_prices.py
On Render:              a Cron Job runs this once a day (see render.yaml)
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
