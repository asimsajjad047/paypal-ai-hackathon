"""
Requirements AI: turns what the user says into numbers the picker understands.

    "£1100, I play Valorant and Cyberpunk at 1440p, I also edit videos"
        -> {"min_gpu_score": 30400, "min_cpu_score": 24000, "min_ram_gb": 32, ...}

Who does what (the project's rule: AI for language and judgement, code for facts):
  * Claude reads the messy English, recognises the games (even ones not in our
    table, by estimating their demand), and picks RAM/storage/resolution.
  * Python checks every number is sensible, then does the FPS maths in
    performance.py. The AI never decides prices or compatibility.
  * With no API key, simple keyword rules do a rougher job of the same thing.
"""
from typing import List, Literal

from pydantic import BaseModel, Field

import ai_client
from db import get_connection
from performance import GAMES, find_game, required_scores

UNKNOWN_GAME = {"gpu": 14000, "cpu": 16000}   # a "medium" modern game, used offline


# ---------- The shape Claude must answer in ----------

class GameDemand(BaseModel):
    name: str = Field(description="Official game title")
    gpu: int = Field(description="GPU benchmark score for ~60 FPS at 1080p high settings")
    cpu: int = Field(description="CPU benchmark score for ~60 FPS at 1080p high settings")


class AIRequirements(BaseModel):
    games: List[GameDemand]
    resolution: Literal["1080p", "1440p", "4K"]
    target_fps: int = Field(description="FPS the user wants; 60 for story games, 144 for competitive")
    min_ram_gb: int
    min_storage_gb: int
    summary: str = Field(description="One friendly sentence restating what the user wants")


SYSTEM = """You are the requirements analyst inside RigAgent, a PC-building agent.
Turn the user's request into hardware requirements.

Benchmark scale (PassMark-style): GPU G3D Mark, e.g. RTX 4060 = 19800, RTX 4070 = 26900,
RTX 4090 = 38000. CPU Mark, e.g. Ryzen 5 5600 = 21500, Ryzen 5 7600 = 27000.

Reference demands (score for ~60 FPS at 1080p high). Copy these exactly for known games,
and estimate on the same scale for any game not listed:
{table}

Rules:
- If the user gives a resolution or FPS, use it. Otherwise choose sensibly from the budget
  and games (competitive shooters -> 144 FPS; story games -> 60 FPS).
- RAM: 16 GB for gaming, 32 GB if they stream, edit video, or play heavy sims. 64 only if asked.
- Storage: at least 1000 GB if they list several big modern games, otherwise 500.
- If they mention no games, include one representative game for their use."""


def _demand_table():
    return "\n".join(f"- {name}: GPU {d['gpu']}, CPU {d['cpu']}" for name, d in GAMES.items())


# ---------- Offline fallback ----------

def _offline(games, resolution, target_fps, notes):
    text = notes.lower()
    demands = []
    for g in games:
        known = find_game(g)
        if known:
            demands.append(dict(GAMES[known], name=known))
        elif g.strip():
            demands.append(dict(UNKNOWN_GAME, name=g.strip()))
    if not demands:
        demands = [dict(GAMES["Fortnite"], name="Fortnite")]

    if not resolution:
        resolution = "4K" if "4k" in text else "1440p" if "1440" in text else "1080p"
    if not target_fps:
        target_fps = max(min(GAMES.get(d["name"], {"fps": 60})["fps"] for d in demands), 60)
    heavy = any(w in text for w in ["stream", "edit", "render", "blender", "sim"])
    return {
        "games": demands,
        "resolution": resolution,
        "target_fps": target_fps,
        "min_ram_gb": 32 if heavy else 16,
        "min_storage_gb": 1000 if len(demands) >= 3 or heavy else 500,
        "summary": f"{', '.join(d['name'] for d in demands)} at {resolution}, ~{target_fps} FPS",
    }


# ---------- Checking the AI's answer ----------

def _clamp(value, low, high):
    return max(low, min(high, int(value)))


def _validate(raw):
    """Never trust model output blindly: force every number into a sane range."""
    games = [{"name": g["name"][:60],
              "gpu": _clamp(g["gpu"], 1000, 60000),
              "cpu": _clamp(g["cpu"], 1000, 60000)} for g in raw["games"][:8]]
    if not games:
        games = [dict(UNKNOWN_GAME, name="General gaming")]
    ram = min([8, 16, 32, 64], key=lambda r: abs(r - raw["min_ram_gb"]))
    return {
        "games": games,
        "resolution": raw["resolution"] if raw["resolution"] in ("1080p", "1440p", "4K") else "1080p",
        "target_fps": _clamp(raw["target_fps"], 30, 240),
        "min_ram_gb": ram,
        "min_storage_gb": _clamp(raw["min_storage_gb"], 250, 4000),
        "summary": raw.get("summary", "")[:300],
    }


def _best_available():
    conn = get_connection()
    try:
        gpu = conn.execute("SELECT MAX(BenchmarkScore) FROM GPU g JOIN Listing l ON l.PartID = g.PartID").fetchone()[0]
        cpu = conn.execute("SELECT MAX(BenchmarkScore) FROM CPU c JOIN Listing l ON l.PartID = c.PartID").fetchone()[0]
    finally:
        conn.close()
    return gpu or 1, cpu or 1


# ---------- Main entry point ----------

def build_requirements(budget, condition="new", games=(), resolution=None,
                       target_fps=None, notes="", min_ram_gb=None, min_storage_gb=None):
    """
    condition: "new", "used" or "both".
    resolution, target_fps, min_ram_gb, min_storage_gb: the user's own choices
    (None = let RigAgent decide). They always win over the AI's guesses.
    Returns (requirements_for_picker, details_for_the_UI)
    """
    games = [g for g in games if g and g.strip()]
    prompt = (f"Budget: £{budget}\nNew/used: {condition}\n"
              f"Games picked: {', '.join(games) or 'none'}\n"
              f"Resolution: {resolution or 'not given'}\nTarget FPS: {target_fps or 'not given'}\n"
              f"What they said: {notes or '(nothing)'}")

    ai = ai_client.ask_json(SYSTEM.format(table=_demand_table()), prompt, AIRequirements)
    source = "Claude" if ai else "offline rules"
    raw = ai.model_dump() if ai else _offline(games, resolution, target_fps, notes)
    # user's explicit choices always win over the AI's guesses
    if resolution:
        raw["resolution"] = resolution
    if target_fps:
        raw["target_fps"] = target_fps
    if min_ram_gb:
        raw["min_ram_gb"] = min_ram_gb
    if min_storage_gb:
        raw["min_storage_gb"] = min_storage_gb
    details = _validate(raw)

    min_gpu, min_cpu = required_scores(details["games"], details["resolution"], details["target_fps"])

    # If nothing on sale is that fast, aim for the best we have and say so
    warnings = []
    best_gpu, best_cpu = _best_available()
    if min_gpu > best_gpu:
        warnings.append(f"Hitting {details['target_fps']} FPS at {details['resolution']} in every game "
                        f"needs a GPU faster than anything listed, so RigAgent aims for the fastest available.")
        min_gpu = best_gpu
    if min_cpu > best_cpu:
        min_cpu = best_cpu

    requirements = {
        "min_gpu_score": min_gpu,
        "min_cpu_score": min_cpu,
        "min_ram_gb": details["min_ram_gb"],
        "min_storage_gb": details["min_storage_gb"],
        "allow_used": condition in ("used", "both"),
        # extra CPU beyond ~1.6x what the games need barely changes FPS
        "cpu_score_cap": max(round(min_cpu * 1.6), 20000),
    }
    details.update({"source": source, "warnings": warnings, "budget": budget,
                    "condition": condition})
    return requirements, details


if __name__ == "__main__":
    req, info = build_requirements(1100, "both", ["Valorant", "Cyberpunk 2077"],
                                   notes="I also stream on Twitch")
    print(info["source"], info["summary"])
    print(req)
