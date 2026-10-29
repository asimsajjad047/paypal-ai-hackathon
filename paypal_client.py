"""
Talks to the PayPal REST API (sandbox). Only HTTP calls live here; the business
logic (which seller gets what, escrow) is in checkout.py.

APIs used:
  OAuth      POST /v1/oauth2/token                       get an access token
  Orders v2  POST /v2/checkout/orders                    create the checkout
             GET  /v2/checkout/orders/{id}               check its status
             POST /v2/checkout/orders/{id}/capture       take the money after approval
  Payouts    POST /v1/payments/payouts                   pay sellers (marketplace mode)
  Payments   POST /v2/payments/captures/{id}/refund      refund the buyer (escrow)

If PAYPAL_CLIENT_ID/SECRET are missing, MockPayPal does the same things in memory
(well, in the database) so the whole flow can still be demoed offline.
"""
import time
import uuid

import requests

import config


class PayPalError(Exception):
    """Raised with PayPal's own error name and message, so the UI can show it."""


class PayPalClient:
    mode_name = "sandbox"

    def __init__(self, client_id=None, secret=None, base_url=None):
        self.client_id = client_id or config.PAYPAL_CLIENT_ID
        self.secret = secret or config.PAYPAL_CLIENT_SECRET
        self.base_url = base_url or config.PAYPAL_BASE_URL
        self._token = None
        self._token_expires = 0

    # ---------- plumbing ----------

    def _access_token(self):
        """Tokens last ~9 hours; reuse it until a minute before it expires."""
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        r = requests.post(f"{self.base_url}/v1/oauth2/token",
                          auth=(self.client_id, self.secret),
                          data={"grant_type": "client_credentials"}, timeout=30)
        if r.status_code != 200:
            raise PayPalError(f"Could not log in to PayPal ({r.status_code}): check PAYPAL_CLIENT_ID/SECRET")
        data = r.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 3000)
        return self._token

    def _request(self, method, path, body=None, idempotency_key=None):
        headers = {"Authorization": f"Bearer {self._access_token()}",
                   "Content-Type": "application/json",
                   "Prefer": "return=representation"}
        if idempotency_key:
            # same key twice = PayPal won't do the action twice (safe retries)
            headers["PayPal-Request-Id"] = idempotency_key
        r = requests.request(method, f"{self.base_url}{path}", json=body, headers=headers, timeout=30)
        if r.status_code >= 400:
            try:
                err = r.json()
                details = "; ".join(f"{d.get('issue')}: {d.get('description', '')}"
                                    for d in err.get("details", []))
                msg = f"{err.get('name', 'ERROR')} - {err.get('message', '')} {details}".strip()
            except ValueError:
                msg = r.text[:300]
            raise PayPalError(f"PayPal {r.status_code}: {msg}")
        return r.json() if r.content else {}

    # ---------- Orders ----------

    def create_order(self, purchase_units, return_url, cancel_url, request_id=None):
        body = {
            "intent": "CAPTURE",
            "purchase_units": purchase_units,
            "payment_source": {"paypal": {"experience_context": {
                "brand_name": "RigAgent",
                "user_action": "PAY_NOW",
                "shipping_preference": "NO_SHIPPING",
                "return_url": return_url,
                "cancel_url": cancel_url,
            }}},
        }
        order = self._request("POST", "/v2/checkout/orders", body, request_id or str(uuid.uuid4()))
        return {"id": order["id"], "status": order["status"], "approval_url": approval_link(order),
                "raw": order}

    def get_order(self, order_id):
        return self._request("GET", f"/v2/checkout/orders/{order_id}")

    def capture_order(self, order_id):
        return self._request("POST", f"/v2/checkout/orders/{order_id}/capture", {},
                             f"capture-{order_id}")

    # ---------- Money after the checkout ----------

    def refund_capture(self, capture_id, amount, currency, note=""):
        body = {"amount": {"value": f"{amount:.2f}", "currency_code": currency},
                "note_to_payer": note[:255] or "Refund from RigAgent"}
        return self._request("POST", f"/v2/payments/captures/{capture_id}/refund", body,
                             f"refund-{capture_id}-{amount:.2f}")

    def payout(self, batch_id, items, currency):
        """items = [{"email", "amount", "note", "ref"}]: send money to sellers."""
        body = {
            "sender_batch_header": {"sender_batch_id": batch_id,
                                    "email_subject": "You have a payment from RigAgent"},
            "items": [{"recipient_type": "EMAIL",
                       "amount": {"value": f"{i['amount']:.2f}", "currency": currency},
                       "receiver": i["email"], "note": i.get("note", "RigAgent sale"),
                       "sender_item_id": i["ref"]} for i in items],
        }
        res = self._request("POST", "/v1/payments/payouts", body)
        return {"batch_id": res["batch_header"]["payout_batch_id"],
                "status": res["batch_header"]["batch_status"]}


class MockPayPal:
    """
    Offline stand-in with the same methods. The 'approval page' is just a link
    back to the app with the order ID, exactly like PayPal's real redirect.
    """
    mode_name = "mock"

    def __init__(self):
        self.orders = {}

    def create_order(self, purchase_units, return_url, cancel_url, request_id=None):
        order_id = "MOCK-" + uuid.uuid4().hex[:12].upper()
        self.orders[order_id] = {"id": order_id, "status": "PAYER_ACTION_REQUIRED",
                                 "purchase_units": purchase_units}
        sep = "&" if "?" in return_url else "?"
        return {"id": order_id, "status": "PAYER_ACTION_REQUIRED",
                "approval_url": f"{return_url}{sep}token={order_id}&PayerID=MOCKBUYER",
                "raw": self.orders[order_id]}

    def get_order(self, order_id):
        return self.orders.get(order_id, {"id": order_id, "status": "APPROVED"})

    def capture_order(self, order_id):
        # the order may have been created in another Streamlit session, so don't rely on memory
        units = self.orders.get(order_id, {}).get("purchase_units", [{"reference_id": "default"}])
        return {"id": order_id, "status": "COMPLETED",
                "purchase_units": [{"reference_id": u.get("reference_id", "default"),
                                    "payments": {"captures": [{"id": f"MOCKCAP-{uuid.uuid4().hex[:8].upper()}",
                                                               "status": "COMPLETED"}]}}
                                   for u in units]}

    def refund_capture(self, capture_id, amount, currency, note=""):
        return {"id": f"MOCKREF-{uuid.uuid4().hex[:8].upper()}", "status": "COMPLETED"}

    def payout(self, batch_id, items, currency):
        return {"batch_id": f"MOCKPAYOUT-{uuid.uuid4().hex[:8].upper()}", "status": "SUCCESS"}


def approval_link(order):
    """PayPal returns several links; the buyer must open the 'payer-action' (or 'approve') one."""
    for link in order.get("links", []):
        if link.get("rel") in ("payer-action", "approve"):
            return link["href"]
    return None


def get_client():
    return PayPalClient() if config.PAYPAL_ENABLED else MockPayPal()
