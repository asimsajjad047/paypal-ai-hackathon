"""
Live PayPal SANDBOX check: run this on your own computer after filling in .env.

    python check_paypal.py

It tests each PayPal call RigAgent uses, one at a time, and prints PASS/FAIL
in plain words. It never prints your keys. It only uses sandbox (test) money.

  1. Log in (OAuth)                      -> are PAYPAL_CLIENT_ID / SECRET right?
  2. Create a checkout (Orders v2)       -> gives you a link to approve in the browser
  3. Read the order back (status)
  4. Pay by test card + capture          -> proves capture works without a browser
  5. Partial refund of that capture      -> escrow "problem: refund me" path
  6. Payout to a seller email            -> marketplace mode pays shops this way
  7. Split mode: one order, 2 sellers    -> needs SELLER_1_EMAIL and SELLER_2_EMAIL
"""
import os
import sys
import uuid

import config
from paypal_client import PayPalClient, PayPalError

CUR = config.PAYPAL_CURRENCY
results = []


def step(name, fn):
    try:
        detail = fn()
        results.append((name, True))
        print(f"PASS  {name}" + (f"  ({detail})" if detail else ""))
        return True
    except PayPalError as e:
        results.append((name, False))
        print(f"FAIL  {name}\n      {e}")
    except Exception as e:                       # anything unexpected: show it plainly
        results.append((name, False))
        print(f"FAIL  {name}\n      {type(e).__name__}: {e}")
    return False


def unit(ref, amount, payee=None):
    u = {"reference_id": ref, "description": "RigAgent sandbox check",
         "amount": {"currency_code": CUR, "value": f"{amount:.2f}"}}
    if payee:
        u["payee"] = {"email_address": payee}
    return u


def main():
    if not config.PAYPAL_ENABLED:
        sys.exit("Put PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env first.")
    print(f"PayPal: {config.PAYPAL_BASE_URL}, currency {CUR}\n")
    pp = PayPalClient()
    state = {}

    if not step("1. Log in to PayPal (OAuth)", lambda: pp._access_token() and None):
        sys.exit("\nStopped: fix the Client ID / Secret first (sandbox app, not live).")

    def create():
        order = pp.create_order([unit("check", 10)], f"{config.APP_BASE_URL}/?paypal=return",
                                f"{config.APP_BASE_URL}/?paypal=cancel")
        state["order"] = order["id"]
        state["link"] = order["approval_url"]
        return f"order {order['id']}, status {order['status']}"
    step("2. Create a checkout", create)

    if "order" in state:
        step("3. Read the order status", lambda: pp.get_order(state["order"])["status"])

    def card_capture():
        body = {"intent": "CAPTURE", "purchase_units": [unit("card", 25)],
                "payment_source": {"card": {"number": "4111111111111111", "expiry": "2030-12",
                                            "name": "RigAgent Test", "security_code": "123"}}}
        order = pp._request("POST", "/v2/checkout/orders", body, str(uuid.uuid4()))
        if order["status"] != "COMPLETED":
            order = pp.capture_order(order["id"])
        cap = order["purchase_units"][0]["payments"]["captures"][0]
        state["capture"] = cap["id"]
        return f"capture {cap['id']} is {cap['status']}"
    card_ok = step("4. Pay by test card and capture", card_capture)

    if card_ok:
        step("5. Partial refund (£5 of £25)",
             lambda: pp.refund_capture(state["capture"], 5, CUR, "RigAgent check")["status"])
    else:
        print("SKIP  5. Refund (needs step 4; card payments may be off for this sandbox app)")

    seller = os.getenv("SELLER_1_EMAIL") or "rigagent-test-seller@business.example.com"
    step("6. Payout £1 to a seller", lambda: pp.payout(f"check-{uuid.uuid4().hex[:10]}",
         [{"email": seller, "amount": 1, "ref": "check-1"}], CUR)["status"])

    s1, s2 = os.getenv("SELLER_1_EMAIL"), os.getenv("SELLER_2_EMAIL")
    if s1 and s2:
        step("7. Split mode: one checkout, two sellers",
             lambda: pp.create_order([unit("seller-1", 10, s1), unit("seller-2", 12, s2)],
                                     f"{config.APP_BASE_URL}/?paypal=return",
                                     f"{config.APP_BASE_URL}/?paypal=cancel")["status"])
    else:
        print("SKIP  7. Split mode (add SELLER_1_EMAIL and SELLER_2_EMAIL to .env)")

    passed = sum(ok for _, ok in results)
    print(f"\n{passed}/{len(results)} checks passed.")
    if state.get("link"):
        print("\nTo try the buyer side, open this link and log in with your sandbox PERSONAL account:")
        print(state["link"])
        print("(It returns to the app's address; run `streamlit run app.py` first to see the result.)")


if __name__ == "__main__":
    main()
