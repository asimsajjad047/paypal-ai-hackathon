from listings import matches_part, sane_price, save_listings
from db import get_connection


def test_matching_rejects_variants_and_junk():
    assert matches_part("MSI GeForce RTX 4070 VENTUS 2X 12G OC", "RTX 4070")
    assert not matches_part("ASUS TUF RTX 4070 Ti Super", "RTX 4070")
    assert not matches_part("RTX 4070 box only", "RTX 4070")
    assert matches_part("Corsair Vengeance 32 GB DDR5 6000MHz", "Vengeance DDR5 32GB")


def test_sane_price():
    assert sane_price(500, 549) and not sane_price(20, 549) and not sane_price(5000, 549)


def test_save_listings_upserts_and_records_history():
    offer = {"source": "channel3", "external_id": "p1:scan.co.uk", "title": "RTX 4070",
             "price": 529.0, "currency": "GBP", "condition": "New", "seller": "scan.co.uk",
             "url": "https://example.com"}
    save_listings(7, [offer])
    save_listings(7, [dict(offer, price=519.0)])       # same listing, new price
    conn = get_connection()
    rows = conn.execute("SELECT Price FROM Listing WHERE Source = 'channel3'").fetchall()
    hist = conn.execute("SELECT Price FROM PriceHistory WHERE Source = 'channel3'").fetchall()
    conn.close()
    assert [r[0] for r in rows] == [519.0]
    assert [h[0] for h in hist] == [519.0]
