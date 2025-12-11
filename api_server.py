# api_server.py

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from simulate_matchup import run_today_matchups, run_custom_matchup

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
    return {"status": "ok"}


@app.get("/odds/today")
def odds_today(trials: int = 20000):
    """
    Returns live-adjusted Monte Carlo odds for all today's matchups.
    """
    data = run_today_matchups(trials=trials)
    return data


@app.get("/odds/custom")
def odds_custom(
    team1: str = Query(..., description="First fantasy team name"),
    team2: str = Query(..., description="Second fantasy team name"),
    trials: int = Query(20000, description="Number of Monte Carlo trials"),
):
    """
    Returns live-adjusted Monte Carlo odds for a specific pair of fantasy teams.
    """
    try:
        return run_custom_matchup(team1, team2, trials=trials)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/")
def index():
    # Serve ./static/index.html at the root
    return FileResponse("static/index.html")
