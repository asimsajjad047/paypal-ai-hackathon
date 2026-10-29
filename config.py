"""
All settings in one place.

Every secret comes from environment variables (your .env file locally, or the
Render dashboard when deployed). If a key is missing, that feature switches to
an OFFLINE fallback so the demo never breaks. See .env.example for the full list.
"""
import os
from dotenv import load_dotenv

load_dotenv()   # reads .env (if it exists) into os.environ


def _get(name, default=""):
    return os.getenv(name, default).strip()


def _flag(name, default=False):
    return _get(name, "true" if default else "false").lower() in ("1", "true", "yes", "on")


# ---------- AI (Claude) ----------
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
AI_MODEL = _get("AI_MODEL", "claude-opus-5-5")
AI_EFFORT = _get("AI_EFFORT", "low")         # low = fast replies, good for a live demo
AI_ENABLED = bool(ANTHROPIC_API_KEY) and not _flag("RIGAGENT_OFFLINE_AI")

# ---------- PayPal ----------
PAYPAL_CLIENT_ID = _get("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = _get("PAYPAL_CLIENT_SECRET")
PAYPAL_BASE_URL = _get("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
PAYPAL_CURRENCY = _get("PAYPAL_CURRENCY", "GBP")
# marketplace = buyer pays RigAgent once, RigAgent pays each seller with Payouts
#               (used parts are held in escrow until the buyer confirms delivery)
# split       = one order with one purchase unit per seller, paid straight to them
PAYPAL_CHECKOUT_MODE = _get("PAYPAL_CHECKOUT_MODE", "marketplace")
PAYPAL_ENABLED = bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)
# From PayPal dashboard -> your app -> Webhooks, after adding <APP_BASE_URL>/paypal/webhook
PAYPAL_WEBHOOK_ID = _get("PAYPAL_WEBHOOK_ID")

# Where PayPal sends the buyer back after approving (your Streamlit URL)
APP_BASE_URL = _get("APP_BASE_URL", "http://localhost:8501").rstrip("/")

# ---------- Part data sources ----------
CHANNEL3_API_KEY = _get("CHANNEL3_API_KEY")
EBAY_CLIENT_ID = _get("EBAY_CLIENT_ID")          # eBay "App ID"
EBAY_CLIENT_SECRET = _get("EBAY_CLIENT_SECRET")  # eBay "Cert ID"
EBAY_BASE_URL = _get("EBAY_BASE_URL", "https://api.ebay.com")

# ---------- Database ----------
DB_PATH = _get("RIGAGENT_DB")   # empty = pcparts.db next to db.py


def status():
    """Which features are live and which are using fallbacks (shown in the app)."""
    return {
        "AI (Claude)": "live" if AI_ENABLED else "offline rules",
        "PayPal": f"sandbox ({PAYPAL_CHECKOUT_MODE})" if PAYPAL_ENABLED else "mock checkout",
        "Channel3": "key set" if CHANNEL3_API_KEY else "no key (test data)",
        "eBay": "key set" if EBAY_CLIENT_ID and EBAY_CLIENT_SECRET else "no key (test data)",
    }
