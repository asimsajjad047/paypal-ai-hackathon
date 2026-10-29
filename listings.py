"""
Shared steps for every price source (Channel3, eBay):

  matches_part()   is this web listing really the part we want?
  save_listings()  upsert into Listing + write today's PriceHistory row
  save_history()   store the price history Channel3 sent us live

Every fetcher normalises its results to the same shape first:
  {source, external_id, title, price, currency, condition, seller, url}
"""
import re
from datetime import date

from db import get_connection

# Words that mean "this isn't a working part" or "wrong product"
JUNK_WORDS = ["laptop", "box only", "empty box", "for parts", "faulty", "broken", "not working",
              "spares", "repair", "bundle", "prebuilt", "pre-built", "gaming pc", "desktop pc",
              "waterblock", "backplate", "bracket", "cable", "fan only", "shroud", "sticker"]

# A part name like "RTX 4070" must not match "RTX 4070 Ti" or "RTX 4070 Super"
VARIANT_WORDS = ["ti", "super", "xt", "xtx", "gre", "x3d"]


def _words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def matches_part(title, part_name, brand=""):
    """
    Keyword check: every word of the part name must be in the title, no junk words,
    and no variant word (Ti, Super, XT...) that our part name doesn't have.
    """
    t = re.sub(r"(\d+)\s*(gb|tb)", r"\1\2", title.lower())   # "32 GB" -> "32gb"
    if any(j in t for j in JUNK_WORDS):
        return False
    title_words = _words(t)
    name_words = [w for w in _words(part_name) if w not in ("gb", "tb")]
    if not all(w in title_words or w in t for w in name_words):
        return False
    extra_variants = [v for v in VARIANT_WORDS if v in title_words and v not in name_words]
    return not extra_variants


def sane_price(price, reference):
    """Reject absurd prices (e.g. £5 GPUs or £9,999 typos): keep 35%-250% of our reference."""
    return reference * 0.35 <= price <= reference * 2.5


def _seller_id(conn, name, source, seller_type):
    """
    Real shop/seller names from the web, but they can't receive sandbox money, so
    each new seller borrows a sandbox email from a seed seller of the same type.
    """
    row = conn.execute("SELECT SellerID FROM Seller WHERE Name = ?", (name,)).fetchone()
    if row:
        return row["SellerID"]
    template = conn.execute(
        "SELECT PayPalEmail, MinPriceFactor FROM Seller WHERE SellerType = ? ORDER BY SellerID LIMIT 1",
        (seller_type,)).fetchone()
    base = template["PayPalEmail"] if template else "seller@business.example.com"
    # PayPalEmail is UNIQUE, so add a +tag (sandbox emails accept it as an alias)
    local, _, domain = base.partition("@")
    n = conn.execute("SELECT COUNT(*) FROM Seller").fetchone()[0]
    email = f"{local}+{source}{n}@{domain}"
    factor = template["MinPriceFactor"] if template else 1.0
    cur = conn.execute("INSERT INTO Seller (Name, PayPalEmail, SellerType, MinPriceFactor) VALUES (?, ?, ?, ?)",
                       (name[:80], email, seller_type, factor))
    return cur.lastrowid


def save_listings(part_id, offers):
    """Upsert normalised offers for one part. Returns how many were saved."""
    today = date.today().isoformat()
    conn = get_connection()
    try:
        for o in offers:
            condition = "Used" if o["condition"] == "Used" else "New"
            seller_type = "Individual" if condition == "Used" and o["source"] == "ebay" else "Shop"
            seller_id = _seller_id(conn, o["seller"], o["source"], seller_type)
            conn.execute("""
                INSERT INTO Listing (PartID, SellerID, Condition, Price, Source, ExternalID, URL, LastSeen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (Source, ExternalID) DO UPDATE SET
                    Price = excluded.Price, LastSeen = excluded.LastSeen, URL = excluded.URL""",
                (part_id, seller_id, condition, o["price"], o["source"], o["external_id"], o["url"], today))
        # one history row per part/condition/source per day: the cheapest price seen
        for condition in ("New", "Used"):
            for source in {o["source"] for o in offers}:
                prices = [o["price"] for o in offers if o["source"] == source and
                          ("Used" if o["condition"] == "Used" else "New") == condition]
                if prices:
                    conn.execute("INSERT OR REPLACE INTO PriceHistory (PartID, Date, Price, Condition, Source) "
                                 "VALUES (?, ?, ?, ?, ?)", (part_id, today, min(prices), condition, source))
        conn.commit()
    finally:
        conn.close()
    return len(offers)


def save_history(part_id, points, condition, source):
    """Write price history fetched live (points = [{"Date", "Price"}]), replacing older copies."""
    conn = get_connection()
    try:
        conn.executemany("INSERT OR REPLACE INTO PriceHistory (PartID, Date, Price, Condition, Source) "
                         "VALUES (?, ?, ?, ?, ?)",
                         [(part_id, p["Date"], p["Price"], condition, source) for p in points])
        conn.commit()
    finally:
        conn.close()


def parts_to_track():
    """Every part with its name, brand and current cheapest test price (the reference)."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.PartID, p.Name, p.Brand, p.Category, MIN(l.Price) AS RefPrice
            FROM Part p JOIN Listing l ON l.PartID = p.PartID
            GROUP BY p.PartID ORDER BY p.PartID""").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
