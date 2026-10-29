import os
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import config

HERE = Path(__file__).parent

# The database file sits in the same folder as this file (unless RIGAGENT_DB says otherwise)
DB_PATH = Path(config.DB_PATH) if config.DB_PATH else HERE / "pcparts.db"


def get_connection():
    """Open the database with the settings RigAgent needs."""
    if not DB_PATH.exists():
        init_db()                            # first run (e.g. on Render): build it
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us use row["Name"] instead of row[0]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite forgets this every time, so set it here
    return conn


def init_db(path=None):
    """
    Delete and rebuild the database from schema.sql + seed.sql.
    Same as the old command:  rm -f pcparts.db && sqlite3 pcparts.db < schema.sql ...
    but also adds 90 days of test price history (for the buy/wait rating).
    """
    path = Path(path) if path else DB_PATH
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.executescript((HERE / "schema.sql").read_text())
        conn.executescript((HERE / "seed.sql").read_text())
        _seed_price_history(conn)
        _use_sandbox_seller_emails(conn)
        conn.commit()
    finally:
        conn.close()


def _seed_price_history(conn, days=90):
    """
    Fake but believable daily prices for every test listing, so buy/wait has
    something to look at before the real price collector has run for weeks.
    Each part gets a trend (falling, rising or flat) picked from its PartID,
    so the numbers are the same every time you rebuild.
    """
    today = date.today()
    rows = conn.execute(
        "SELECT PartID, Condition, MIN(Price) FROM Listing GROUP BY PartID, Condition").fetchall()
    for part_id, condition, price_now in rows:
        rng = random.Random(part_id * 10 + (condition == "Used"))
        trend = rng.choice([-0.15, -0.08, 0.0, 0.0, 0.06, 0.12])  # total change over the period
        for d in range(days, -1, -1):
            # walk backwards from today's price: older days are "before the trend"
            progress = d / days
            noise = rng.uniform(-0.03, 0.03)
            price = price_now * (1 - trend * progress + noise) if d else price_now
            conn.execute(
                "INSERT OR REPLACE INTO PriceHistory (PartID, Date, Price, Condition, Source) "
                "VALUES (?, ?, ?, ?, 'test')",
                (part_id, (today - timedelta(days=d)).isoformat(), round(price, 2), condition))


def _use_sandbox_seller_emails(conn):
    """
    The seed uses example.com emails. Swap in your real SANDBOX business accounts
    with SELLER_1_EMAIL=..., SELLER_2_EMAIL=... in .env (number = SellerID).
    """
    for (seller_id,) in conn.execute("SELECT SellerID FROM Seller").fetchall():
        email = os.getenv(f"SELLER_{seller_id}_EMAIL", "").strip()
        if email:
            conn.execute("UPDATE Seller SET PayPalEmail = ? WHERE SellerID = ?", (email, seller_id))


# Runs only when you do: python db.py
if __name__ == "__main__":
    init_db()
    conn = get_connection()
    for table in ["Part", "Listing", "Seller", "PriceHistory"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<13} {n} rows")
    conn.close()
    print(f"Rebuilt {DB_PATH}")
