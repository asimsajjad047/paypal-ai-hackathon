import sqlite3
from pathlib import Path

# The database file sits in the same folder as this file
DB_PATH = Path(__file__).parent / "pcparts.db"


def get_connection():
    """Open the database with the settings RigAgent needs."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us use row["Name"] instead of row[0]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite forgets this every time, so set it here
    return conn