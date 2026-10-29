from compatibility import check_build
from performance import GAMES, estimate_fps, find_game, required_scores
from picker import pick_build

REQ = {"min_gpu_score": 20000, "min_cpu_score": 15000, "min_ram_gb": 16,
       "min_storage_gb": 500, "allow_used": False}


def test_good_build_passes_all_rules():
    results = check_build(1, 3, 5, 7, 8, 9, 10)
    assert all(r["passed"] for r in results)
    assert len(results) == 8


def test_bad_build_fails_most_rules():
    results = check_build(2, 3, 6, 12, 13, 14, 10)
    assert sum(r["passed"] for r in results) == 2


def test_picker_stays_in_budget_and_meets_minimums():
    for budget in (900, 1100, 2000):
        build, _ = pick_build(budget, REQ)
        assert build is not None
        assert build["total"] <= budget
        assert build["parts"]["GPU"]["Benchmark"] >= REQ["min_gpu_score"]
        assert build["parts"]["CPU"]["Benchmark"] >= REQ["min_cpu_score"]


def test_picker_says_when_budget_too_small():
    build, message = pick_build(300, REQ)
    assert build is None
    assert "Cheapest build" in message


def test_used_parts_only_when_allowed():
    build, _ = pick_build(1100, REQ)
    assert all(p["Condition"] == "New" for p in build["parts"].values())


def test_fps_maths():
    cyberpunk = dict(GAMES["Cyberpunk 2077"], name="Cyberpunk 2077")
    gpu, cpu = required_scores([cyberpunk], "1440p", 60)
    assert estimate_fps(cyberpunk, gpu, 60000, "1440p")["fps"] == 60
    assert estimate_fps(cyberpunk, 60000, 1000, "1080p")["bottleneck"] == "CPU"
    assert find_game("cs2") == "Counter-Strike 2"
