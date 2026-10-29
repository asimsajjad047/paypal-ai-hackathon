"""
RigAgent's look: animated gradient background, liquid-metal logo, glass panels and
an interactive 3D model of the build.

The visuals are written in React (frontend/src) and built once into static/rigagent3d.js,
which Streamlit serves at /app/static/ (see .streamlit/config.toml). Each function here
mounts a tiny st.components.v2 component whose JavaScript loads that file and draws
into the page. Python never needs Node: the built file is committed.

Rebuild after changing frontend/src:   cd frontend && npm install && npm run build
"""
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
BUNDLE = HERE / "static" / "rigagent3d.js"
CSS = (HERE / "static" / "rigagent.css").read_text(encoding="utf-8")

# The ?v= changes whenever the bundle is rebuilt, so browsers don't keep an old copy.
_VERSION = int(BUNDLE.stat().st_mtime) if BUNDLE.exists() else 0


def _loader(kind):
    """JavaScript for one component: load the shared bundle, then draw `kind`."""
    return f"""
const base = window.location.origin + window.location.pathname.replace(/[^/]*$/, "");
export default async function (component) {{
  const ui = await import(new URL("app/static/rigagent3d.js?v={_VERSION}", base).href);
  return ui.mount("{kind}", component);
}}
"""


# isolate_styles=False: draw straight into the page (no shadow DOM), so rigagent.css applies.
_background = st.components.v2.component("rig_background", js=_loader("background"), isolate_styles=False)
_logo = st.components.v2.component("rig_logo", js=_loader("logo"), isolate_styles=False)
_build3d = st.components.v2.component("rig_build3d", js=_loader("build3d"), isolate_styles=False)


def setup(effects=True):
    """Call once at the top of every run: glass styling + the moving background."""
    st.html(f"<style>{CSS}</style>")
    _background(key="rig-bg", data={"enabled": effects, "calm": False}, height=0)


def logo(size=64, key="logo", effects=True):
    _logo(key=key, data={"size": size, "key": key, "animate": effects}, width=size, height=size)


def hero(effects=True):
    """Logo + headline for the Design page."""
    c1, c2 = st.columns([1, 6], vertical_alignment="center")
    with c1:
        logo(84, key="hero-logo", effects=effects)
    c2.html('<div class="rig-hero"><h1>RigAgent</h1>'
            '<p>Your AI PC builder. Design, haggle, pay once with PayPal.</p></div>')


def build_3d(build, agreed=None, selected=None, effects=True):
    """
    Interactive 3D model of the build. Returns the category the user clicked
    ("GPU", "Case", ...), "" if they clicked empty space, or None if nothing happened.
    """
    agreed = agreed or {}
    parts = []
    for cat, p in build["parts"].items():
        parts.append({"category": cat, "name": p["Name"], "condition": p["Condition"],
                      "seller": p["Seller"], "price": float(agreed.get(p["ListingID"], p["Price"])),
                      "sticks": 4 if cat == "RAM" and p.get("Capacity_GB", 0) >= 64 else 2})
    result = _build3d(key="build-3d", data={"parts": parts, "selected": selected, "animate": effects,
                                            "key": "build"},
                      height=420, on_selected_change=lambda: None)
    return result.selected if result is not None else None
