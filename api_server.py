# api_server.py

import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import demo_mode

# Only import live modules when demo mode is off (they trigger ESPN API calls on import)
_DEMO = demo_mode.DEMO_ENABLED
if not _DEMO:
    from simulate_matchup import run_today_matchups, run_custom_matchup
    from weekly_sim import run_weekly_matchups
    from patch_missing_players import main as patch_missing_players_main

app = FastAPI(title="Fantasy Live Odds API")

# CORS for mobile / other frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from ./static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": _DEMO}


# ─── Main odds endpoints ───────────────────────────────────────────────────────

@app.get("/odds/today")
def odds_today(trials: int = 20000):
    """
    Returns live-adjusted Monte Carlo odds for all today's matchups.
    In demo mode: serves cached data with clock-based live game progression.
    """
    if _DEMO:
        return demo_mode.run_demo_today()
    data = run_today_matchups(trials=trials)
    return data


@app.get("/odds/weekly")
def odds_weekly(trials: int = 20000):
    """
    Returns weekly Monte Carlo odds for all current matchups.
    In demo mode: serves cached data with live today-state overlaid.
    """
    if _DEMO:
        return demo_mode.run_demo_weekly()
    data = run_weekly_matchups(trials=10000, save=True)
    return data


@app.get("/odds/custom")
def odds_custom(
    team1: str = Query(..., description="First fantasy team name"),
    team2: str = Query(..., description="Second fantasy team name"),
    trials: int = Query(20000, description="Number of Monte Carlo trials"),
):
    """
    Returns live-adjusted Monte Carlo odds for a specific pair of fantasy teams.
    Not available in demo mode.
    """
    if _DEMO:
        raise HTTPException(
            status_code=503,
            detail="Custom matchup not available in demo mode. Disable DEMO_DATE to use this endpoint.",
        )
    try:
        return run_custom_matchup(team1, team2, trials=trials)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/patch_missing_players")
def patch_missing_players():
    if _DEMO:
        raise HTTPException(status_code=503, detail="Not available in demo mode.")
    try:
        patch_missing_players_main()
        return {"status": "success", "message": "Missing players patched successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Demo control endpoints ────────────────────────────────────────────────────

@app.get("/demo/status")
def demo_status():
    """Show current demo clock state and configuration."""
    return demo_mode.get_demo_status()


@app.post("/demo/reset")
def demo_reset():
    """
    Restart the demo clock — games go back to 0% complete.
    The frontend's live indicators will reset to pre-game state.
    """
    if not _DEMO:
        raise HTTPException(status_code=400, detail="Demo mode is not active. Set DEMO_DATE env var.")
    return demo_mode.reset_demo_clock()


@app.post("/demo/set-speed")
def demo_set_speed(speed: float = Query(..., description="New speed multiplier (e.g. 1, 3, 10, 60)")):
    """Change the clock speed without moving the current game position."""
    if not _DEMO:
        raise HTTPException(status_code=400, detail="Demo mode is not active.")
    return demo_mode.set_demo_speed(speed)


@app.post("/demo/set-fraction")
def demo_set_fraction(fraction: float = Query(..., description="Game fraction 0.0–1.0 to jump to")):
    """Jump directly to any point in the simulated game day."""
    if not _DEMO:
        raise HTTPException(status_code=400, detail="Demo mode is not active.")
    return demo_mode.set_demo_fraction(fraction)


@app.post("/demo/skip")
def demo_skip(hours: float = Query(1.0, description="Simulated hours to skip forward")):
    """
    Fast-forward the demo clock by N simulated hours.
    Examples:
      /demo/skip?hours=2.5  → jump to halfway through a 5-hour game window
      /demo/skip?hours=5    → jump to games finished
      /demo/skip?hours=-1   → rewind 1 hour
    """
    if not _DEMO:
        raise HTTPException(status_code=400, detail="Demo mode is not active. Set DEMO_DATE env var.")
    return demo_mode.skip_demo_clock(hours)


@app.get("/")
def index():
    return FileResponse("static/index.html")
