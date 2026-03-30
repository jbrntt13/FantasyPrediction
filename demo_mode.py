"""
Demo mode for FantasyPrediction backend.

Replays a historical week of fantasy basketball as if games are happening right now.
Uses only local cached JSON files — no ESPN API, no NBA API needed.

Configure via environment variables:
  DEMO_DATE=2026-02-06     Date to simulate as "today" (needs a _weekly_odds.json for that week)
  DEMO_SPEED=1.0           Clock speed multiplier (3.0 = games progress 3x faster)
  DEMO_GAME_WINDOW=5.0     Simulated hours for the game day (default 5 = ~7pm to midnight)

Control endpoints (when server is running):
  POST /demo/reset          Restart clock from 0
  POST /demo/skip?hours=1   Fast-forward N simulated hours
  GET  /demo/status         Show current clock state
"""

import os
import json
import time
from datetime import date, timedelta
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────

DEMO_DATE_STR: str | None = os.environ.get("DEMO_DATE")
DEMO_SPEED: float = float(os.environ.get("DEMO_SPEED", "1.0"))
DEMO_GAME_WINDOW: float = float(os.environ.get("DEMO_GAME_WINDOW", "5.0"))
DEMO_ENABLED: bool = bool(DEMO_DATE_STR)

if DEMO_ENABLED:
    DEMO_DATE: date = date.fromisoformat(DEMO_DATE_STR)
    _wd = DEMO_DATE.weekday()          # Monday = 0
    DEMO_WEEK_START: date = DEMO_DATE - timedelta(days=_wd)
    DEMO_WEEK_END: date = DEMO_WEEK_START + timedelta(days=6)
    print(
        f"\n[demo_mode] *** DEMO MODE ACTIVE ***\n"
        f"  Simulating date : {DEMO_DATE}\n"
        f"  Demo week       : {DEMO_WEEK_START} → {DEMO_WEEK_END}\n"
        f"  Speed           : {DEMO_SPEED}x\n"
        f"  Game window     : {DEMO_GAME_WINDOW}h simulated\n"
        f"  Expected caches : {DEMO_WEEK_START}_weekly_odds.json + {DEMO_DATE}_projScore.json\n"
    )
else:
    DEMO_DATE = None
    DEMO_WEEK_START = None
    DEMO_WEEK_END = None


# ─── Clock management ─────────────────────────────────────────────────────────

_clock_start: float | None = None


def _get_clock_start() -> float:
    global _clock_start
    if _clock_start is None:
        _clock_start = time.time()
    return _clock_start


def reset_demo_clock() -> dict:
    """Reset clock so games are back at 0% complete."""
    global _clock_start
    _clock_start = time.time()
    return {
        "reset_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "demo_date": DEMO_DATE_STR,
        "speed": DEMO_SPEED,
        "game_fraction": 0.0,
    }


def skip_demo_clock(hours: float = 1.0) -> dict:
    """
    Fast-forward by `hours` of simulated game time.
    Example: skip(2.5) jumps to the halfway point of a 5-hour game window.
    """
    global _clock_start
    # Shifting clock_start back advances elapsed time
    _clock_start = _get_clock_start() - (hours * 3600.0 / DEMO_SPEED)
    return get_demo_status()


def _game_fraction() -> float:
    """Return how far through the game window we are: 0.0 = pre-game, 1.0 = all done."""
    elapsed_real = time.time() - _get_clock_start()
    elapsed_sim = elapsed_real * DEMO_SPEED
    total_sim = DEMO_GAME_WINDOW * 3600.0
    return max(0.0, min(1.0, elapsed_sim / total_sim))


def set_demo_speed(new_speed: float) -> dict:
    """Change speed while holding the current game position steady."""
    global DEMO_SPEED, _clock_start
    new_speed = max(0.1, float(new_speed))
    current_frac = _game_fraction()
    DEMO_SPEED = new_speed
    total_sim_s = DEMO_GAME_WINDOW * 3600.0
    # Shift clock_start so current_frac stays the same under the new speed
    _clock_start = time.time() - (current_frac * total_sim_s / new_speed)
    return get_demo_status()


def set_demo_fraction(fraction: float) -> dict:
    """Jump directly to any point in the game day (0.0 = pre-game, 1.0 = final)."""
    global _clock_start
    fraction = max(0.0, min(1.0, float(fraction)))
    total_sim_s = DEMO_GAME_WINDOW * 3600.0
    _clock_start = time.time() - (fraction * total_sim_s / DEMO_SPEED)
    return get_demo_status()


def get_demo_status() -> dict:
    frac = _game_fraction()
    elapsed_sim_h = (time.time() - _get_clock_start()) * DEMO_SPEED / 3600.0
    return {
        "enabled": DEMO_ENABLED,
        "demo_date": DEMO_DATE_STR,
        "demo_week_start": DEMO_WEEK_START.isoformat() if DEMO_WEEK_START else None,
        "demo_week_end": DEMO_WEEK_END.isoformat() if DEMO_WEEK_END else None,
        "speed": DEMO_SPEED,
        "game_window_hours": DEMO_GAME_WINDOW,
        "elapsed_real_seconds": round(time.time() - _get_clock_start(), 1),
        "elapsed_sim_hours": round(elapsed_sim_h, 2),
        "game_fraction": round(frac, 3),
        "is_live": 0.0 < frac < 1.0,
        "hint": "POST /demo/reset to restart | POST /demo/skip?hours=N to fast-forward",
    }


# ─── Cache loaders ────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | None:
    if not path.exists():
        print(f"[demo_mode] cache not found: {path}")
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _weekly_cache() -> dict | None:
    return _load_json(Path(f"{DEMO_WEEK_START.isoformat()}_weekly_odds.json"))


def _daily_cache() -> dict | None:
    return _load_json(Path(f"{DEMO_DATE.isoformat()}_projScore.json"))


# ─── run_demo_today ───────────────────────────────────────────────────────────

def run_demo_today() -> dict:
    """
    Demo replacement for simulate_matchup.run_today_matchups().

    Returns today's odds with current scores simulated via clock fraction.
    Prefers the daily projScore cache for win probs and daily projections;
    falls back to the weekly cache's daily_scores if projScore is missing.
    """
    daily = _daily_cache()
    weekly = _weekly_cache()

    if not daily and not weekly:
        return {
            "error": (
                "No demo cache found. "
                f"Need {DEMO_DATE}_projScore.json or {DEMO_WEEK_START}_weekly_odds.json"
            )
        }

    demo_today_str = DEMO_DATE.isoformat()

    # Build per-team lookup for today's projected score and win probability.
    # The projScore cache has values from the actual day simulation (most accurate).
    # The weekly cache's daily_scores is the fallback.
    today_proj: dict[str, float] = {}
    today_win_probs: dict[str, float] = {}
    today_tie_probs: dict[str, float] = {}
    team_urls: dict[str, str] = {}
    matchup_pairs: list[tuple[str, str]] = []

    if daily:
        for m in daily.get("matchups", []):
            h, a = m["home_team"], m["away_team"]
            today_proj[h] = float(m.get("home_avg", 0.0))
            today_proj[a] = float(m.get("away_avg", 0.0))
            today_win_probs[h] = float(m.get("home_win_prob", 0.5))
            today_win_probs[a] = float(m.get("away_win_prob", 0.5))
            today_tie_probs[h] = float(m.get("tie_prob", 0.0))
            today_tie_probs[a] = float(m.get("tie_prob", 0.0))
            team_urls[h] = m.get("home_team_url", "")
            team_urls[a] = m.get("away_team_url", "")
            matchup_pairs.append((h, a))

    elif weekly:
        for m in weekly.get("matchups", []):
            h, a = m["home_team"], m["away_team"]
            ds = m.get("daily_scores", {}).get(demo_today_str, {})
            today_proj[h] = float(ds.get("team1", m.get("home_avg", 0.0) / 7))
            today_proj[a] = float(ds.get("team2", m.get("away_avg", 0.0) / 7))
            today_win_probs[h] = 0.5
            today_win_probs[a] = 0.5
            today_tie_probs[h] = 0.0
            today_tie_probs[a] = 0.0
            team_urls[h] = m.get("home_team_url", "")
            team_urls[a] = m.get("away_team_url", "")
            matchup_pairs.append((h, a))

    frac = _game_fraction()
    is_live = 0.0 < frac < 1.0

    results = []
    current_scores: dict[str, float] = {}
    proj_scores: dict[str, float] = {}
    win_probs: dict[str, float] = {}

    for home, away in matchup_pairs:
        h_proj = today_proj.get(home, 0.0)
        a_proj = today_proj.get(away, 0.0)
        h_current = round(h_proj * frac, 2)
        a_current = round(a_proj * frac, 2)

        results.append({
            "home_team": home,
            "away_team": away,
            "home_avg": h_proj,
            "away_avg": a_proj,
            "home_win_prob": today_win_probs.get(home, 0.5),
            "away_win_prob": today_win_probs.get(away, 0.5),
            "tie_prob": today_tie_probs.get(home, 0.0),
            "trials": 10000,
            "home_team_url": team_urls.get(home, ""),
            "away_team_url": team_urls.get(away, ""),
            "home_current_score": h_current,
            "away_current_score": a_current,
        })

        current_scores[home] = h_current
        current_scores[away] = a_current
        proj_scores[home] = h_proj
        proj_scores[away] = a_proj
        win_probs[home] = today_win_probs.get(home, 0.5)
        win_probs[away] = today_win_probs.get(away, 0.5)

    return {
        "date": demo_today_str,
        "is_live": is_live,
        "matchups": results,
        "proj_scores": proj_scores,
        "current_scores": current_scores,
        "win_probs": win_probs,
        "demo_mode": True,
        "demo_speed": DEMO_SPEED,
        "game_fraction": round(frac, 3),
    }


# ─── run_demo_weekly ──────────────────────────────────────────────────────────

def run_demo_weekly() -> dict:
    """
    Demo replacement for weekly_sim.run_weekly_matchups().

    Returns weekly odds with live today-state overlaid using clock fraction.

    Weekly projected scores and win probabilities come from the cached weekly_odds.
    The "today live" layer is computed by run_demo_today() and merged in.

    home_current_score  = base accumulated score (Mon-day_before_demo) + today partial
    home_today_score    = today's partial score so far (daily_proj × fraction)
    home_today_remaining_proj = projected remaining today
    home_today_total_proj     = full projected daily score
    """
    weekly = _weekly_cache()
    if not weekly:
        return {
            "error": (
                f"No weekly cache for week of {DEMO_WEEK_START}. "
                f"Need file: {DEMO_WEEK_START}_weekly_odds.json"
            )
        }

    today_data = run_demo_today()
    if "error" in today_data:
        return today_data

    today_current = today_data.get("current_scores", {})
    today_proj_map = today_data.get("proj_scores", {})
    is_live = today_data.get("is_live", False)
    frac = _game_fraction()
    demo_today_str = DEMO_DATE.isoformat()

    matchups = []

    for m in weekly.get("matchups", []):
        home, away = m["home_team"], m["away_team"]

        # Today's projected daily total and current partial score
        h_today_proj = today_proj_map.get(
            home,
            float(m.get("daily_scores", {}).get(demo_today_str, {}).get("team1", 0.0)),
        )
        a_today_proj = today_proj_map.get(
            away,
            float(m.get("daily_scores", {}).get(demo_today_str, {}).get("team2", 0.0)),
        )
        h_today_current = today_current.get(home, round(h_today_proj * frac, 2))
        a_today_current = today_current.get(away, round(a_today_proj * frac, 2))
        h_today_remaining = round(max(0.0, h_today_proj - h_today_current), 2)
        a_today_remaining = round(max(0.0, a_today_proj - a_today_current), 2)

        # Base accumulated score = ESPN total captured BEFORE today's games started.
        # This is stored as home_current_score in the weekly cache (which was generated
        # before today's games began, so it reflects Mon-Thu accumulated total).
        h_base = float(m.get("home_current_score", 0.0))
        a_base = float(m.get("away_current_score", 0.0))

        h_total = round(h_base + h_today_current, 2)
        a_total = round(a_base + a_today_current, 2)

        # Clone daily_scores and update today's entry with live values
        daily_scores = dict(m.get("daily_scores", {}))
        if demo_today_str in daily_scores:
            daily_scores[demo_today_str] = {
                "team1": h_today_current,
                "team2": a_today_current,
            }

        matchups.append({
            "home_team": home,
            "away_team": away,
            "home_avg": m["home_avg"],
            "away_avg": m["away_avg"],
            "home_win_prob": m["home_win_prob"],
            "away_win_prob": m["away_win_prob"],
            "tie_prob": m["tie_prob"],
            "trials": m.get("trials", 10000),
            "home_team_url": m["home_team_url"],
            "away_team_url": m["away_team_url"],
            "daily_scores": daily_scores,
            "home_current_score": h_total,
            "away_current_score": a_total,
            "home_today_score": h_today_current,
            "away_today_score": a_today_current,
            "home_today_total_proj": h_today_proj,
            "away_today_total_proj": a_today_proj,
            "home_today_remaining_proj": h_today_remaining,
            "away_today_remaining_proj": a_today_remaining,
        })

    return {
        "week_start": DEMO_WEEK_START.isoformat(),
        "week_end": DEMO_WEEK_END.isoformat(),
        "matchups": matchups,
        "proj_scores": weekly.get("proj_scores", {}),
        "win_probs": weekly.get("win_probs", {}),
        "current_scores": today_current,   # same shape as live (today's scores only)
        "is_live": is_live,
        "date": demo_today_str,
        "demo_mode": True,
        "demo_speed": DEMO_SPEED,
        "game_fraction": round(frac, 3),
    }
