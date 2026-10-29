"""
Live prices, tested with FAKE Channel3 answers (tests never call real websites).
"""
from datetime import date, timedelta

import buy_wait
import config
import fetch_channel3
import live_prices
from agent import build_as_rows, design_build
from db import get_connection


def fake_search(part, limit=20, client=None):
    """Every part is on sale at a real shop for 5% less than its test price."""
    return [{"source": "channel3", "external_id": f"prod{part['PartID']}:scan.co.uk",
             "title": f"{part['Brand']} {part['Name']}", "price": round(part["RefPrice"] * 0.95, 2),
             "currency": "GBP", "condition": "New", "seller": "scan.co.uk",
             "url": f"https://www.scan.co.uk/{part['PartID']}", "product_id": f"prod{part['PartID']}"}]


def fake_history(product_id, client=None, days=90):
    """30 days of a price falling £2 a day, and Channel3 saying today's price is low."""
    today = date.today()
    return {"history": [{"Date": (today - timedelta(days=29 - i)).isoformat(), "Price": 600.0 - 2 * i}
                        for i in range(30)],
            "status": "low", "low": 542.0, "high": 600.0}


def go_live(monkeypatch):
    monkeypatch.setattr(config, "CHANNEL3_API_KEY", "fake-key")
    monkeypatch.setattr(fetch_channel3, "_client", lambda: None)
    monkeypatch.setattr(fetch_channel3, "search_part", fake_search)
    monkeypatch.setattr(fetch_channel3, "price_history", fake_history)


def test_no_keys_means_test_prices_and_no_live_calls():
    assert not live_prices.enabled()
    result = design_build(1100, "new", ["Valorant"], explain=False)
    assert result["live"] is None
    assert all(p["Source"] == "test" for p in result["build"]["parts"].values())


def test_build_uses_real_listings_found_during_the_request(monkeypatch):
    go_live(monkeypatch)
    result = design_build(1100, "new", ["Valorant"], explain=False)
    parts = result["build"]["parts"].values()
    assert result["live"]["real_parts"] == len(parts) == 8
    assert result["live"]["sources"] == ["channel3"]
    assert all(p["Source"] == "channel3" and "scan.co.uk" in p["URL"] for p in parts)
    assert {r["Source"] for r in build_as_rows(result["build"])} == {"Live (Channel3)"}


def test_buy_wait_uses_live_history_not_test_history(monkeypatch):
    go_live(monkeypatch)
    result = design_build(1100, "new", ["Valorant"], explain=False)
    ratings = buy_wait.rate_build(result["build"]["parts"])
    gpu = ratings["GPU"]
    assert gpu["history_source"] == "real"
    assert len(gpu["history"]) == 30            # only Channel3's points, no test points mixed in
    assert "Channel3 rates today's price as low" in gpu["reason"]


def test_turning_live_prices_off(monkeypatch):
    go_live(monkeypatch)
    monkeypatch.setattr(config, "LIVE_PRICES", False)
    assert design_build(1100, "new", ["Valorant"], explain=False)["live"] is None


def test_old_real_listings_lose_to_test_prices():
    """A real listing last seen a week ago may be sold, so it no longer jumps the queue."""
    conn = get_connection()
    test_price = conn.execute("SELECT MIN(Price) FROM Listing WHERE PartID = 7 AND Condition = 'New'").fetchone()[0]
    conn.execute("INSERT INTO Listing (PartID, SellerID, Condition, Price, Source, ExternalID, LastSeen) "
                 "VALUES (7, 1, 'New', ?, 'channel3', 'old', ?)",
                 (test_price + 50, (date.today() - timedelta(days=7)).isoformat()))
    conn.commit()
    conn.close()
    from picker import get_options
    gpu = next(p for p in get_options(False)["GPU"] if p["PartID"] == 7)
    assert gpu["Source"] == "test" and gpu["Price"] == test_price
