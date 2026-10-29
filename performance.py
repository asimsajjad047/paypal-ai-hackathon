"""
Performance estimator: "how many FPS will I get in Cyberpunk?"

Plain maths, no AI. Each game has a "demand": the GPU and CPU benchmark scores
needed for about 60 FPS at 1080p, high settings. FPS then scales with how much
stronger (or weaker) your parts are, and the slower of the two (GPU or CPU)
is the bottleneck.

The numbers are rough estimates for a demo, not lab measurements.
"""

# GPU/CPU score for ~60 FPS at 1080p high. "fps" = a sensible default target.
GAMES = {
    "Valorant":                {"gpu": 5000,  "cpu": 11000, "fps": 144},
    "League of Legends":       {"gpu": 4000,  "cpu": 9000,  "fps": 144},
    "Counter-Strike 2":        {"gpu": 9000,  "cpu": 15000, "fps": 144},
    "Fortnite":                {"gpu": 11000, "cpu": 14000, "fps": 120},
    "Apex Legends":            {"gpu": 11000, "cpu": 14000, "fps": 120},
    "Rocket League":           {"gpu": 5000,  "cpu": 9000,  "fps": 144},
    "Minecraft":               {"gpu": 5000,  "cpu": 10000, "fps": 60},
    "Roblox":                  {"gpu": 3000,  "cpu": 8000,  "fps": 60},
    "GTA V":                   {"gpu": 8000,  "cpu": 12000, "fps": 60},
    "Call of Duty: Warzone":   {"gpu": 15000, "cpu": 18000, "fps": 120},
    "Elden Ring":              {"gpu": 14000, "cpu": 15000, "fps": 60},
    "Red Dead Redemption 2":   {"gpu": 16000, "cpu": 16000, "fps": 60},
    "Baldur's Gate 3":         {"gpu": 15000, "cpu": 20000, "fps": 60},
    "Cyberpunk 2077":          {"gpu": 19000, "cpu": 18000, "fps": 60},
    "Starfield":               {"gpu": 21000, "cpu": 22000, "fps": 60},
    "Black Myth: Wukong":      {"gpu": 21000, "cpu": 18000, "fps": 60},
    "Microsoft Flight Simulator": {"gpu": 20000, "cpu": 24000, "fps": 60},
}

# Higher resolution = more pixels = the GPU has to work harder
RESOLUTION_FACTOR = {"1080p": 1.0, "1440p": 1.6, "4K": 2.8}

# A CPU that "just" hits 60 FPS in a game can usually push ~1.5x that before
# it holds the GPU back, so CPU demand is scaled down a bit.
CPU_HEADROOM = 1.5


def find_game(name):
    """Case-insensitive lookup that also accepts small differences ('cs2', 'gta 5')."""
    aliases = {"cs2": "Counter-Strike 2", "csgo": "Counter-Strike 2", "lol": "League of Legends",
               "gta 5": "GTA V", "gta5": "GTA V", "warzone": "Call of Duty: Warzone",
               "cyberpunk": "Cyberpunk 2077", "rdr2": "Red Dead Redemption 2",
               "bg3": "Baldur's Gate 3", "msfs": "Microsoft Flight Simulator"}
    key = name.strip().lower()
    if key in aliases:
        return aliases[key]
    for game in GAMES:
        if game.lower() == key or game.lower().startswith(key):
            return game
    return None


def required_scores(game_demands, resolution, target_fps):
    """
    game_demands: list of {"name", "gpu", "cpu"} (60 FPS at 1080p numbers)
    Returns the minimum GPU and CPU scores to hit target_fps in EVERY game.
    """
    res = RESOLUTION_FACTOR.get(resolution, 1.0)
    min_gpu = max(g["gpu"] * res * target_fps / 60 for g in game_demands)
    min_cpu = max(g["cpu"] * target_fps / 60 / CPU_HEADROOM for g in game_demands)
    return round(min_gpu), round(min_cpu)


def estimate_fps(game, gpu_score, cpu_score, resolution):
    """
    game: {"name", "gpu", "cpu"}. Returns {"fps", "bottleneck"}.
    """
    res = RESOLUTION_FACTOR.get(resolution, 1.0)
    gpu_fps = 60 * gpu_score / (game["gpu"] * res)
    cpu_fps = 60 * cpu_score * CPU_HEADROOM / game["cpu"]
    fps = min(gpu_fps, cpu_fps)
    bottleneck = "GPU" if gpu_fps <= cpu_fps else "CPU"
    return {"fps": int(min(fps, 360)), "bottleneck": bottleneck}


def fps_table(build_parts, game_demands, resolution):
    """FPS estimate for each game with this build (for the results page)."""
    gpu = build_parts["GPU"]["Benchmark"]
    cpu = build_parts["CPU"]["Benchmark"]
    rows = []
    for g in game_demands:
        est = estimate_fps(g, gpu, cpu, resolution)
        rows.append({"Game": g["name"], "Resolution": resolution,
                     "Estimated FPS": est["fps"], "Limited by": est["bottleneck"]})
    return rows


if __name__ == "__main__":
    games = [dict(GAMES[n], name=n) for n in ["Valorant", "Cyberpunk 2077"]]
    print("Needed for 1440p @ 60:", required_scores(games, "1440p", 60))
    for g in games:
        print(g["name"], estimate_fps(g, gpu_score=26900, cpu_score=27000, resolution="1440p"))
