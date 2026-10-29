import buy_wait
from agent import design_build
from negotiation import negotiate
from requirements_ai import _validate, build_requirements


def test_offline_requirements_from_games():
    req, details = build_requirements(1100, "both", ["Valorant", "Cyberpunk 2077"],
                                      resolution="1440p", notes="I stream too")
    assert details["source"] == "offline rules"
    assert req["allow_used"] is True
    assert req["min_ram_gb"] == 32            # streaming -> 32 GB
    assert req["min_gpu_score"] > 20000       # Cyberpunk at 1440p is demanding


def test_unknown_game_still_works():
    _, details = build_requirements(1000, "new", ["Some Indie Game 3"])
    assert details["games"][0]["name"] == "Some Indie Game 3"


def test_ai_output_is_clamped():
    raw = {"games": [{"name": "X", "gpu": 999999, "cpu": -5}], "resolution": "8K",
           "target_fps": 1000, "min_ram_gb": 30, "min_storage_gb": 1, "summary": "s"}
    v = _validate(raw)
    assert v["games"][0]["gpu"] == 60000 and v["games"][0]["cpu"] == 1000
    assert v["resolution"] == "1080p" and v["target_fps"] == 240
    assert v["min_ram_gb"] == 32 and v["min_storage_gb"] == 250


def test_design_build_end_to_end():
    r = design_build(1100, "both", ["Fortnite"])
    assert r["ok"] and r["explanation"] and r["fps"]
    assert all(c["passed"] for c in r["checks"])


def test_negotiation_never_breaks_limits():
    for max_price in (250, 300, 330, 380):
        r = negotiate(13, max_price)            # used RTX 4070, asking £380, floor £323
        for t in r["transcript"]:
            if t["who"] == "buyer":
                assert t["price"] <= max_price
            else:
                assert t["price"] >= 380 * 0.85 - 0.01
        if r["deal"]:
            assert 323 <= r["final_price"] <= max_price
        else:
            assert max_price < 323 or r["final_price"] is None


def test_slope_and_black_friday():
    assert buy_wait.slope_per_day([10, 9, 8, 7]) == -1
    from datetime import date
    assert buy_wait.days_to_black_friday(date(2026, 11, 20)) == 7   # BF 2026 = 27 Nov


def test_rate_part_gives_a_rating():
    r = buy_wait.rate_part(7, 549)
    assert r["rating"] in ("Buy now", "Fair", "Wait") and r["history"]
