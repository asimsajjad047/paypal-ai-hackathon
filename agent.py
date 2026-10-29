"""
RigAgent's main pipeline, in one place, so the Streamlit app and the MCP server
do exactly the same thing:

    words -> requirements (AI) -> pick parts (code) -> check rules (code)
          -> FPS estimate (code) -> explanation (AI)
"""
import explain_ai
from compatibility import check_build
from performance import fps_table
from picker import pick_build
from requirements_ai import build_requirements


def design_build(budget, condition="new", games=(), resolution=None, target_fps=None,
                 notes="", explain=True):
    """
    Returns a dict:
      ok, message, requirements, details, build, checks, fps, explanation
    (build is None, and ok is False, if nothing fits the budget)
    """
    requirements, details = build_requirements(budget, condition, games, resolution, target_fps, notes)
    build, message = pick_build(budget, requirements)
    result = {"ok": build is not None, "message": message, "requirements": requirements,
              "details": details, "build": build, "checks": [], "fps": [], "explanation": ""}
    if build is None:
        return result

    p = build["parts"]
    result["checks"] = check_build(p["CPU"]["PartID"], p["Motherboard"]["PartID"], p["RAM"]["PartID"],
                                   p["GPU"]["PartID"], p["PSU"]["PartID"], p["Case"]["PartID"],
                                   p["Cooler"]["PartID"])
    result["fps"] = fps_table(p, details["games"], details["resolution"])
    if explain:
        result["explanation"] = explain_ai.explain_build(build, details, result["fps"], result["checks"])
    return result


def build_as_rows(build, agreed_prices=None):
    """Table rows for showing a build (used by the app and the MCP server)."""
    agreed_prices = agreed_prices or {}
    rows = []
    for cat, part in build["parts"].items():
        price = agreed_prices.get(part["ListingID"], part["Price"])
        rows.append({"Part": cat, "Name": part["Name"], "Condition": part["Condition"],
                     "Seller": part["Seller"], "Price (£)": round(price, 2),
                     "ListingID": part["ListingID"]})
    return rows
