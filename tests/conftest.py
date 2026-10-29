"""
Test setup: use a throwaway database and force every outside service OFF,
so tests never need keys, never spend money and never touch your real pcparts.db.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Must happen BEFORE config.py is imported (it reads these once)
os.environ["RIGAGENT_DB"] = str(ROOT / "tests" / "test.db")
os.environ["RIGAGENT_OFFLINE_AI"] = "true"
for key in ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "CHANNEL3_API_KEY",
            "EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET"]:
    os.environ[key] = ""

import pytest  # noqa: E402

import db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Every test starts from the same seed data."""
    db.init_db()
    yield
