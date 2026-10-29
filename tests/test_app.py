"""Clicks through the Streamlit app like a user would (no browser needed)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _click(at, label):
    next(b for b in at.button if b.label.startswith(label)).click().run()
    assert not at.exception, at.exception


def test_full_journey_design_to_paid():
    at = AppTest.from_file(APP, default_timeout=60).run()
    next(r for r in at.radio if r.label == "Parts").set_value("New + used")
    _click(at, "Build my PC")
    assert at.session_state.page == "Build"
    _click(at, "Haggle")
    _click(at, "Start haggling")
    _click(at, "Continue to checkout")
    at.checkbox[0].check().run()
    _click(at, "Approve and pay")
    order_id = at.session_state.checkout["order_id"]

    back = AppTest.from_file(APP, default_timeout=60)
    back.query_params["paypal"] = "return"
    back.query_params["token"] = order_id
    back.run()
    assert not back.exception
    assert any("Paid" in s.value for s in back.success)


def test_other_pages_render():
    at = AppTest.from_file(APP, default_timeout=60).run()
    for page in ["Orders", "Price watch", "About", "Build"]:
        at.session_state["goto"] = page
        at.run()
        assert not at.exception, page
