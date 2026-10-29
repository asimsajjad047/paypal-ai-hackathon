"""
Runs the Streamlit app AND a webhook URL in one process, so both use the same
database file:

    streamlit run server.py      -> app at /, PayPal webhooks at /paypal/webhook

(`streamlit run app.py` still works when you don't need webhooks, e.g. locally:
PayPal can't reach your laptop anyway.)
"""
import streamlit as st
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.routing import Route

import webhooks


async def paypal_webhook(request):
    raw = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    # database and PayPal calls are normal (blocking) code, so run them off the event loop
    status, message = await run_in_threadpool(webhooks.receive, headers, raw)
    return JSONResponse({"result": message}, status_code=status)


async def health(request):
    return JSONResponse({"status": "ok"})


app = st.App("app.py", routes=[Route("/paypal/webhook", paypal_webhook, methods=["POST"]),
                              Route("/healthz", health)])
