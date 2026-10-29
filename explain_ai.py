"""
Explanation AI: tells the user, in plain English, why RigAgent chose this build.

Claude only gets FACTS that our code worked out (parts, prices, FPS estimates,
compatibility results, upgrades). It is asked to explain them, not invent new
ones. Without a key, a template writes a shorter explanation from the same facts.
"""
import json

import ai_client

SYSTEM = """You are RigAgent, a friendly PC-building expert talking to a first-time builder.
Explain the build you are given in under 200 words of Markdown:
1. One sentence on who this build is for.
2. Why the GPU and CPU were chosen (link them to the user's games and FPS estimates).
3. One trade-off or thing to know (bottleneck, upgrade path, used parts, leftover budget).
Only use the facts provided. Never change prices or claim parts that aren't listed.
Use £ for money."""


def _facts(build, details, fps_rows, checks):
    return {
        "user_wants": details.get("summary"),
        "budget": details.get("budget"),
        "total_price": round(build["total"], 2),
        "left_over": round(details.get("budget", 0) - build["total"], 2),
        "platform": build["platform"],
        "parts": {cat: {"name": p["Name"], "price": p["Price"], "condition": p["Condition"],
                        "seller": p["Seller"]} for cat, p in build["parts"].items()},
        "upgrades_made_with_leftover_budget": build["upgrades"],
        "fps_estimates": fps_rows,
        "compatibility_checks_passed": f"{sum(c['passed'] for c in checks)}/{len(checks)}",
    }


def _template(facts):
    parts = facts["parts"]
    lines = [f"**This build is for:** {facts['user_wants']}.", ""]
    lines.append(f"The **{parts['GPU']['name']}** does most of the work in games, paired with a "
                 f"**{parts['CPU']['name']}** on the {facts['platform']} platform.")
    if facts["fps_estimates"]:
        slowest = min(facts["fps_estimates"], key=lambda r: r["Estimated FPS"])
        lines.append(f"Your most demanding game, {slowest['Game']}, should run at about "
                     f"{slowest['Estimated FPS']} FPS ({slowest['Limited by']} is the limit).")
    used = [f"{v['name']} ({k})" for k, v in parts.items() if v["condition"] == "Used"]
    if used:
        lines.append(f"Used parts save money: {', '.join(used)}. Payment for these is held "
                     "until you confirm they arrived working.")
    if facts["upgrades_made_with_leftover_budget"]:
        lines.append("Upgrades bought with spare budget: "
                     + "; ".join(facts["upgrades_made_with_leftover_budget"]) + ".")
    if facts["left_over"] > 20:
        lines.append(f"£{facts['left_over']:.0f} of your budget is left over, because the next "
                     "upgrade wouldn't fit.")
    lines.append(f"All {facts['compatibility_checks_passed']} compatibility checks passed.")
    return "\n".join(lines)


def explain_build(build, details, fps_rows, checks):
    facts = _facts(build, details, fps_rows, checks)
    text = ai_client.ask_text(SYSTEM, "Explain this build:\n" + json.dumps(facts, indent=2))
    return text or _template(facts)
