"""
RigAgent's main pipeline, in one place, so the Streamlit app and the MCP server
do exactly the same thing:

    words -> requirements (AI) -> pick parts (code) -> live prices (Channel3/eBay)
          -> pick again with real listings -> check rules (code)
          -> FPS estimate (code) -> explanation (AI)
"""
import explain_ai
import live_prices
from compatibility import check_build
from performance import fps_table
from picker import get_options, is_compatible, meets_minimum, score, total
from requirements_ai import build_requirements


def design_build(budget, condition="new", games=(), resolution=None, target_fps=None,
                 notes="", explain=True, min_ram_gb=None, min_storage_gb=None):
    """
    Returns a dict:
      ok, message, requirements, details, build, checks, fps, explanation, live
    (build is None, and ok is False, if nothing fits the budget;
     live is None when prices come from test data)
    """
    requirements, details = build_requirements(budget, condition, games, resolution, target_fps,
                                               notes, min_ram_gb, min_storage_gb)
    build, message, live = live_prices.pick(budget, requirements)
    result = {"ok": build is not None, "message": message, "requirements": requirements,
              "details": details, "build": build, "checks": [], "fps": [], "explanation": "",
              "live": live}
    if build is None:
        return result
    return _analyse(result, explain)


def _analyse(result, explain=True):
    """Compatibility checks, FPS table and explanation for result["build"]."""
    build, details = result["build"], result["details"]
    p = build["parts"]
    result["checks"] = check_build(p["CPU"]["PartID"], p["Motherboard"]["PartID"], p["RAM"]["PartID"],
                                   p["GPU"]["PartID"], p["PSU"]["PartID"], p["Case"]["PartID"],
                                   p["Cooler"]["PartID"])
    result["fps"] = fps_table(p, details["games"], details["resolution"])
    if explain:
        result["explanation"] = explain_ai.explain_build(build, details, result["fps"], result["checks"])
    return result


# ---------- Swapping a part ----------

def alternatives(result, category):
    """
    Other parts for one slot that still fit with the rest of the build,
    cheapest first. Each has "diff" (price change) and "meets_minimum".
    """
    build, req = result["build"], result["requirements"]
    current = build["parts"][category]
    alts = []
    for option in get_options(req["allow_used"])[category]:
        if option["PartID"] == current["PartID"]:
            continue
        trial = dict(build["parts"], **{category: option})
        if not is_compatible(trial):      # the 8 rules still decide
            continue
        alts.append(dict(option, diff=round(option["Price"] - current["Price"], 2),
                         meets_minimum=meets_minimum(option, req)))
    return alts


def swap_part(result, category, new_part, explain=True):
    """Put new_part in the build and redo the checks, FPS and explanation."""
    old = result["build"]["parts"][category]
    new_part = {k: v for k, v in new_part.items() if k not in ("diff", "meets_minimum")}
    parts = dict(result["build"]["parts"], **{category: new_part})
    build = dict(result["build"], parts=parts, total=total(parts),
                 score=score(parts, result["requirements"].get("cpu_score_cap")),
                 upgrades=result["build"]["upgrades"] + [f"You swapped {category}: {old['Name']} → {new_part['Name']}"])
    return _analyse(dict(result, build=build), explain)


SOURCE_NAMES = {"test": "Test price", "channel3": "Live (Channel3)", "ebay": "Live (eBay)"}


def build_as_rows(build, agreed_prices=None):
    """Table rows for showing a build (used by the app and the MCP server)."""
    agreed_prices = agreed_prices or {}
    rows = []
    for cat, part in build["parts"].items():
        price = agreed_prices.get(part["ListingID"], part["Price"])
        rows.append({"Part": cat, "Name": part["Name"], "Condition": part["Condition"],
                     "Seller": part["Seller"], "Price (£)": round(price, 2),
                     "Source": SOURCE_NAMES.get(part.get("Source"), part.get("Source")),
                     "ListingID": part["ListingID"]})
    return rows
