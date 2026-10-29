"""
RigAgent web app (Streamlit).   Run:  streamlit run app.py

Pages (sidebar):  Design -> Build -> Haggle -> Checkout -> Orders,  plus Price watch / About
Everything the user has done so far lives in st.session_state, because
Streamlit re-runs this whole file on every click.
"""
import altair as alt
import streamlit as st

import agent
import buy_wait
import checkout
import collect_prices
import config
import negotiation
import watcher
from db import init_db
from paypal_client import PayPalError
from performance import GAMES

st.set_page_config(page_title="RigAgent", page_icon="🖥️", layout="centered")

PAGES = ["Design", "Build", "Haggle", "Checkout", "Orders", "Price watch", "About"]
RATING_COLOUR = {"Buy now": "green", "Fair": "blue", "Wait": "orange"}
state = st.session_state
state.setdefault("result", None)     # last design_build() result
state.setdefault("agreed", {})       # {ListingID: negotiated price}
state.setdefault("deals", {})        # {ListingID: negotiation result}
state.setdefault("checkout", None)   # last create_checkout() result


def go(page):
    """Switch page on the next run (a widget's value can't change after it's drawn)."""
    state.goto = page
    st.rerun()


def money(x):
    return f"£{x:,.2f}"


# ---------- Coming back from PayPal ----------

def handle_paypal_return():
    """PayPal sends the buyer to ?paypal=return&token=ORDER_ID (or ?paypal=cancel)."""
    qp = st.query_params
    action, order_id = qp.get("paypal"), qp.get("token")
    if not action or not order_id:
        return False
    st.title("🖥️ RigAgent")
    if action == "cancel":
        checkout.cancel_checkout(order_id)
        st.warning("Payment cancelled on PayPal. Nothing was charged.")
    else:
        with st.spinner("Confirming your payment with PayPal..."):
            try:
                summary = checkout.capture_checkout(order_id)
            except (PayPalError, ValueError) as e:
                st.error(f"Couldn't complete the payment: {e}")
                summary = None
        if summary and summary["order"]["Status"] == "COMPLETED":
            st.success(f"Paid {money(summary['order']['Total'])} in one PayPal checkout. 🎉")
            show_order(summary)
        elif summary:
            st.info(f"PayPal says the order is {summary['order']['Status']}.")
    if st.button("Back to RigAgent", type="primary"):
        st.query_params.clear()
        go("Orders")
    return True


# ---------- Shared bits ----------

def show_order(summary):
    o = summary["order"]
    st.caption(f"Order {o['OrderID']} · mode: {o['Mode']} · status: {o['Status']}")
    st.dataframe(summary["items"], hide_index=True)
    st.markdown("**Where the money went**")
    for p in summary["payments"]:
        icon = {"Paid": "✅", "Held": "🔒", "Refunded": "↩️", "Failed": "⚠️"}.get(p["Status"], "⏳")
        st.write(f"{icon} **{p['Seller']}** {money(p['Amount'])} · {p['Status']}"
                 + (f" · {p['Note']}" if p["Note"] else ""))


def price_chart(history):
    """Small 90-day price line. zero=False so a £5 change is actually visible."""
    chart = alt.Chart(alt.Data(values=history)).mark_line().encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0, tickCount=4)),
        y=alt.Y("Price:Q", title="£", scale=alt.Scale(zero=False)),
        tooltip=["Date:T", "Price:Q"])
    st.altair_chart(chart.properties(height=110))


def need_build():
    if state.result is None or not state.result["ok"]:
        st.info("Design a build first.")
        if st.button("Go to Design"):
            go("Design")
        st.stop()


# ---------- Pages ----------

def page_design():
    st.title("🖥️ RigAgent")
    st.write("Tell me your budget and what you play. I'll design a compatible PC, haggle for used "
             "parts, tell you whether to buy now or wait, and check out every seller in **one PayPal payment**.")
    with st.form("design"):
        budget = st.number_input("Budget (£)", min_value=300, max_value=6000, value=1100, step=50)
        condition = st.radio("Parts", ["New only", "New + used", "Used where possible"], horizontal=True)
        games = st.multiselect("Games you play", list(GAMES), default=["Valorant", "Cyberpunk 2077"])
        other = st.text_input("Other games (comma separated)", placeholder="e.g. Helldivers 2, Hogwarts Legacy")
        c1, c2 = st.columns(2)
        resolution = c1.selectbox("Resolution", ["Let RigAgent decide", "1080p", "1440p", "4K"])
        fps = c2.selectbox("Target FPS", ["Let RigAgent decide", 60, 120, 144, 240])
        notes = st.text_area("Anything else?", placeholder="I stream on Twitch, want it quiet, small desk...")
        submitted = st.form_submit_button("Build my PC", type="primary")
    if submitted:
        all_games = games + [g.strip() for g in other.split(",") if g.strip()]
        cond = {"New only": "new", "New + used": "both", "Used where possible": "used"}[condition]
        with st.spinner("Working out what you need and picking parts..."):
            state.result = agent.design_build(
                budget, cond, all_games,
                None if resolution.startswith("Let") else resolution,
                None if fps == "Let RigAgent decide" else int(fps), notes)
        state.agreed, state.deals, state.checkout = {}, {}, None
        state.pop("ratings", None)
        go("Build")


def page_build():
    need_build()
    r = state.result
    build, details = r["build"], r["details"]
    st.title("Your build")
    st.caption(f"Requirements by {details['source']}: {details['summary']}")
    for w in details["warnings"]:
        st.warning(w)

    total = sum(state.agreed.get(p["ListingID"], p["Price"]) for p in build["parts"].values())
    c1, c2, c3 = st.columns(3)
    c1.metric("Total", money(total), delta=f"{money(details['budget'] - total)} under budget",
              delta_color="off")
    c2.metric("Platform", build["platform"])
    c3.metric("Checks passed", f"{sum(c['passed'] for c in r['checks'])}/{len(r['checks'])}")
    st.caption(r["message"])

    st.dataframe(agent.build_as_rows(build, state.agreed), hide_index=True,
                 column_order=["Part", "Name", "Condition", "Seller", "Price (£)"])

    st.subheader("Why this build")
    st.markdown(r["explanation"])

    st.subheader("Estimated FPS")
    st.dataframe(r["fps"], hide_index=True)

    with st.expander("Compatibility checklist (checked by code, not AI)"):
        for c in r["checks"]:
            st.write(f"{'✅' if c['passed'] else '❌'} **{c['rule']}**: {c['detail']}")

    st.subheader("Buy now or wait?")
    if "ratings" not in state:
        with st.spinner("Checking price trends..."):
            state.ratings = buy_wait.rate_build(build["parts"])
            state.advice = buy_wait.summarise(build["parts"], state.ratings)
    st.info(state.advice)
    for cat, rating in state.ratings.items():
        part = build["parts"][cat]
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{cat}: {part['Name']}** · {money(part['Price'])}")
            with c2:
                st.badge(rating["rating"], color=RATING_COLOUR[rating["rating"]])
            st.caption(f"{rating['reason']} (confidence {rating['confidence']:.0%})")
            if rating["history"]:
                price_chart(rating["history"])

    used = [p for p in build["parts"].values() if p["Condition"] == "Used"]
    c1, c2 = st.columns(2)
    if used and c1.button(f"Haggle for {len(used)} used part(s)"):
        go("Haggle")
    if c2.button("Review and pay", type="primary"):
        go("Checkout")


def page_haggle():
    need_build()
    st.title("Haggle for used parts")
    st.write("RigAgent's buyer agent negotiates with each seller's agent. Your maximum is a hard "
             "limit enforced in Python: the AI can't go over it, whatever it says.")
    used = [(cat, p) for cat, p in state.result["build"]["parts"].items() if p["Condition"] == "Used"]
    if not used:
        st.info("This build has no used parts. Choose 'New + used' on the Design page to include some.")
        return
    for cat, part in used:
        lid = part["ListingID"]
        with st.container(border=True):
            st.markdown(f"**{cat}: {part['Name']}** from {part['Seller']}, asking {money(part['Price'])}")
            max_price = st.slider("My maximum (£)", min_value=int(part["Price"] * 0.5),
                                  max_value=int(part["Price"]), value=int(part["Price"] * 0.95),
                                  key=f"max-{lid}")
            if st.button("Start haggling", key=f"go-{lid}"):
                def show(entry):
                    with st.chat_message("user" if entry["who"] == "buyer" else "assistant",
                                         avatar="🛒" if entry["who"] == "buyer" else "🏷️"):
                        st.write(f"**{entry['who'].title()}:** {entry['message']}  \n"
                                 f"`{entry['action']} £{entry['price']:.0f}`")
                        if "guard" in entry:
                            st.caption(f"🛡️ {entry['guard']}")
                with st.spinner("Agents are negotiating..."):
                    state.deals[lid] = negotiation.negotiate(lid, max_price, on_message=show)
                if state.deals[lid]["deal"]:
                    state.agreed[lid] = state.deals[lid]["final_price"]
                else:
                    state.agreed.pop(lid, None)
            elif lid in state.deals:
                with st.expander("Last negotiation"):
                    for e in state.deals[lid]["transcript"]:
                        st.write(f"**{e['who'].title()}:** {e['message']} (`{e['action']} £{e['price']:.0f}`)")
            deal = state.deals.get(lid)
            if deal and deal["deal"]:
                st.success(f"Deal at {money(deal['final_price'])}, saving {money(deal['saved'])} "
                           f"({deal['agents']} agents)")
            elif deal:
                st.warning("No deal within your limit. You can still buy at the asking price, "
                           "or go back and pick new parts.")
    if st.button("Continue to checkout", type="primary"):
        go("Checkout")


def page_checkout():
    need_build()
    r = state.result
    build = r["build"]
    st.title("Review and pay")
    rows = agent.build_as_rows(build, state.agreed)
    st.dataframe(rows, hide_index=True, column_order=["Part", "Name", "Condition", "Seller", "Price (£)"])
    total = sum(row["Price (£)"] for row in rows)
    sellers = sorted({row["Seller"] for row in rows})
    st.metric("Total", money(total))
    st.write(f"**One PayPal payment** pays all {len(sellers)} sellers: {', '.join(sellers)}.")
    if any(p["Condition"] == "Used" for p in build["parts"].values()) and config.PAYPAL_CHECKOUT_MODE != "split":
        st.caption("🔒 Money for used parts is held in escrow until you confirm they arrived working.")
    if not config.PAYPAL_ENABLED:
        st.caption("Demo mode: no PayPal keys set, so this uses a mock checkout.")

    if state.checkout is None:
        ok = st.checkbox("I've checked the parts and approve this purchase")
        if st.button("Approve and pay with PayPal", type="primary", disabled=not ok):
            with st.spinner("Creating your PayPal checkout..."):
                try:
                    state.checkout = checkout.create_checkout(build, r["details"], state.agreed)
                except PayPalError as e:
                    st.error(str(e))
                    st.stop()
            st.rerun()
    else:
        c = state.checkout
        st.success(f"PayPal order {c['order_id']} created for {money(c['total'])}.")
        for s in c["sellers"]:
            st.write(f"- {s['name']}: {money(s['amount'])}" + (" (escrow)" if s["escrow"] else ""))
        if c["approval_url"]:
            st.link_button("Pay with PayPal", c["approval_url"], type="primary")
            st.caption("You'll approve the payment on PayPal's own page, then come back here.")
        if st.button("Start a new build"):
            state.result, state.checkout = None, None
            go("Design")


def page_orders():
    st.title("Orders")
    orders = checkout.list_orders()
    if not orders:
        st.info("No orders yet.")
        return
    labels = {f"{o['OrderID']} · {money(o['Total'])} · {o['Status']}": o["OrderID"] for o in orders}
    order_id = labels[st.selectbox("Order", list(labels))]
    if st.button("Refresh status from PayPal"):
        try:
            checkout.refresh_status(order_id)
        except PayPalError as e:
            st.error(str(e))
    summary = checkout.order_summary(order_id)
    show_order(summary)
    held = [p for p in summary["payments"] if p["Status"] == "Held"]
    if held:
        st.subheader("Used parts in escrow")
    for p in held:
        with st.container(border=True):
            st.write(f"**{p['Seller']}**: {money(p['Amount'])} held")
            c1, c2 = st.columns(2)
            try:
                if c1.button("Arrived and works: pay seller", key=f"ok-{p['PaymentID']}"):
                    checkout.confirm_delivery(p["PaymentID"])
                    st.rerun()
                if c2.button("Problem: refund me", key=f"bad-{p['PaymentID']}"):
                    checkout.report_problem(p["PaymentID"])
                    st.rerun()
            except (PayPalError, ValueError) as e:
                st.error(str(e))


def page_watch():
    st.title("Price watch")
    st.write("For parts rated **Wait**: set a target price. When the price collector sees it, "
             "RigAgent prepares the PayPal order so buying is one tap.")
    ratings = state.get("ratings", {})
    parts = state.result["build"]["parts"] if state.result and state.result["ok"] else {}
    if parts:
        with st.form("watch"):
            options = {f"{cat}: {p['Name']} (now {money(p['Price'])}"
                       + (f", {ratings[cat]['rating']}" if cat in ratings else "") + ")": p
                       for cat, p in parts.items()}
            choice = options[st.selectbox("Part", list(options))]
            c1, c2 = st.columns(2)
            target = c1.number_input("Buy when price ≤ (£)", min_value=1.0, value=float(round(choice["Price"] * 0.9)))
            limit = c2.number_input("Pre-approved max (£)", min_value=1.0, value=float(round(choice["Price"] * 0.95)))
            if st.form_submit_button("Watch this part"):
                watcher.add_watch(choice["PartID"], target, limit, choice["Condition"] == "Used")
                st.success("Watching.")
    else:
        st.caption("Design a build to add watches for its parts.")

    if config.CHANNEL3_API_KEY or config.EBAY_CLIENT_ID:
        if st.button("Fetch live prices (Channel3 + eBay)"):
            with st.spinner("Fetching prices for every part (takes a minute)..."):
                collect_prices.main()
            st.success("Prices updated. Redesign your build to use them.")
    if st.button("Check prices now"):
        hits = watcher.check_watches()
        for h in hits:
            st.success(f"{h['Name']} hit {money(h['price'])}.")
            st.link_button("Approve on PayPal", h["approval_url"])
        if not hits:
            st.info("No watched part has reached its target yet.")
    watches = watcher.list_watches()
    if watches:
        st.dataframe([{"Part": w["Name"], "Target £": w["TargetPrice"], "Max £": w["MaxPrice"],
                       "Status": w["Status"], "Order": w["OrderID"] or ""} for w in watches], hide_index=True)


def page_about():
    st.title("How RigAgent works")
    st.markdown("""
**AI for language and judgement, code for facts, money and safety.**

| Step | Who does it |
|---|---|
| Understand your needs, recognise games, pick RAM/storage | Claude (structured JSON), checked by Python |
| FPS maths, part picking, 8 compatibility rules | Python + SQLite |
| Explain the build, advise buy/wait | Claude, only from facts the code worked out |
| Buy/wait rating | Price trend (least squares), 90-day range, Black Friday rule |
| Haggling | Buyer and seller agents (Claude), with hard price limits enforced in Python |
| Payment | One PayPal checkout for every seller; escrow for used parts; refunds |
| Other AIs | MCP server: `design_build`, `rate_timing`, `negotiate`, `create_checkout` |

**Honest limits:** PayPal runs in sandbox (test money). Sellers are sandbox business accounts
standing in for real shops; prices and parts come from Channel3 (new) and eBay (used) when keys
are set, otherwise from test data. Seller negotiation agents are simulated, as a preview of
agent-to-agent commerce. Nothing is ever bought without you approving it on PayPal.
""")


# ---------- Layout ----------

if handle_paypal_return():
    st.stop()

if "goto" in state:
    state.page = state.pop("goto")
with st.sidebar:
    st.header("🖥️ RigAgent")
    st.radio("Go to", PAGES, key="page", label_visibility="collapsed")
    st.divider()
    st.caption("Services")
    for name, value in config.status().items():
        st.caption(f"{name}: {value}")
    if st.button("Reset demo data"):
        init_db()
        for k in ["result", "checkout", "ratings"]:
            state.pop(k, None)
        state.agreed, state.deals = {}, {}
        st.rerun()

{"Design": page_design, "Build": page_build, "Haggle": page_haggle, "Checkout": page_checkout,
 "Orders": page_orders, "Price watch": page_watch, "About": page_about}[state.get("page", "Design")]()
