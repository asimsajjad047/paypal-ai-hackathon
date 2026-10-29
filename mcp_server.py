"""
RigAgent as an MCP server, so other AI assistants (Claude Desktop, ChatGPT, ...)
can design builds, check timing, haggle and start a PayPal checkout.

Tools:
  design_build      plain-English needs -> compatible build + FPS + explanation
  rate_timing       Buy now / Fair / Wait for every part of a build
  negotiate         haggle for a used listing within a hard maximum
  create_checkout   one PayPal checkout for the whole build -> approval LINK

Safety: create_checkout only returns a link. A human must open it and approve
on PayPal's own page; no AI can spend money through this server.

Run (stdio, for Claude Desktop):   python mcp_server.py
Run over HTTP (e.g. on Render):    python mcp_server.py --http
Claude Desktop config (claude_desktop_config.json):
  {"mcpServers": {"rigagent": {"command": "/full/path/.venv/bin/python",
                               "args": ["/full/path/mcp_server.py"]}}}
"""
import os
import sys

from mcp.server.mcpserver import MCPServer

import agent
import buy_wait
import checkout
import negotiation

server = MCPServer("RigAgent")

# design_build results kept in memory so later tools can refer to them by ID
_builds = {}


@server.tool()
def design_build(budget_gbp: float, games: list[str], condition: str = "new",
                 resolution: str = "", target_fps: int = 0, notes: str = "",
                 ram_gb: int = 0, storage_gb: int = 0) -> dict:
    """Design a compatible gaming PC within a budget in GBP.
    condition: "new", "used" or "both". resolution: "1080p", "1440p" or "4K" (optional).
    notes: anything else the user said, in plain English. ram_gb/storage_gb: 0 = decide for me.
    Returns a build_id to use with the other tools."""
    result = agent.design_build(budget_gbp, condition, games, resolution or None,
                                target_fps or None, notes,
                                min_ram_gb=ram_gb or None, min_storage_gb=storage_gb or None)
    if not result["ok"]:
        return {"ok": False, "message": result["message"]}
    build_id = f"b{len(_builds) + 1}"
    _builds[build_id] = result
    return {"ok": True, "build_id": build_id, "message": result["message"],
            "total_gbp": result["build"]["total"],
            "parts": agent.build_as_rows(result["build"]),
            "fps_estimates": result["fps"],
            "compatibility": [f"{'PASS' if c['passed'] else 'FAIL'} {c['rule']}" for c in result["checks"]],
            "explanation": result["explanation"]}


@server.tool()
def rate_timing(build_id: str) -> dict:
    """Rate each part of a build as Buy now / Fair / Wait, with the reason."""
    result = _builds.get(build_id)
    if result is None:
        return {"error": "Unknown build_id; call design_build first"}
    parts = result["build"]["parts"]
    ratings = buy_wait.rate_build(parts)
    return {"ratings": {cat: {"part": parts[cat]["Name"], "price_gbp": parts[cat]["Price"],
                              "rating": r["rating"], "confidence": r["confidence"], "reason": r["reason"]}
                        for cat, r in ratings.items()},
            "advice": buy_wait.summarise(parts, ratings)}


@server.tool()
def negotiate(listing_id: int, max_price_gbp: float, build_id: str = "") -> dict:
    """Haggle with the seller of a USED listing. Never pays more than max_price_gbp.
    If build_id is given, the agreed price is used at checkout."""
    r = negotiation.negotiate(listing_id, max_price_gbp)
    if build_id in _builds and r["deal"]:
        _builds[build_id].setdefault("agreed", {})[listing_id] = r["final_price"]
    return {"deal": r["deal"], "final_price_gbp": r["final_price"], "asking_gbp": r["asking"],
            "saved_gbp": r["saved"],
            "transcript": [f"{t['who']}: {t['message']}" for t in r["transcript"]]}


@server.tool()
def create_checkout(build_id: str) -> dict:
    """Create ONE PayPal checkout that pays every seller in the build.
    Returns an approval URL. A human must open it and approve the payment on PayPal."""
    result = _builds.get(build_id)
    if result is None:
        return {"error": "Unknown build_id; call design_build first"}
    order = checkout.create_checkout(result["build"], result["details"], result.get("agreed"))
    return {"approval_url": order["approval_url"], "order_id": order["order_id"],
            "total": order["total"], "currency": order["currency"], "sellers": order["sellers"],
            "note": "Nothing has been paid. Open approval_url to review and approve on PayPal."}


if __name__ == "__main__":
    if "--http" in sys.argv:
        server.run("streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
    else:
        server.run()
