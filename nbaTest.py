import requests
import os
import json
from datetime import datetime, date
from typing import Set, Optional
import time

team_name_mapping = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls',
    'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',
    'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic',
    'PHL': 'Philadelphia 76ers', 'PHO': 'Phoenix Suns', 'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings',
    'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
}

TEAM_CODE_CANON = {
    "PHX": "PHX",
    "PHO": "PHX",   # collapse PHO → PHX
    "NOP": "NOP",
    "NO": "NOP",
    "NOK": "NOP",
    "GS": "GSW",
    "GSW": "GSW",
    "SA": "SAS",
    "SAS": "SAS",
    # add more aliases here if you bump into them
}

RATE_LIMIT_SECONDS = 5

def canonical_team(code: str | None) -> str | None:
    if code is None:
        return None
    return TEAM_CODE_CANON.get(code.upper(), code.upper())


def fetch_nba_live_games():
    url = "https://api-nba-v1.p.rapidapi.com/games"

    querystring = {"live": "all"}

    headers = {
        "x-rapidapi-key": "d4bfbc4596msh7f5df671e47c27dp1af307jsn849a11cfef2a",
        "x-rapidapi-host": "api-nba-v1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    return response.json()


def fetch_nba_schedule(path: str = None):
    """
    Load the full NBA schedule from a local JSON file instead of an HTTP API.
    Default: scheduleLeagueV2.json in the same directory as this file.
    """
    if path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "scheduleLeagueV2.json")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data



# Load once at module import
SCHEDULE_DATA = fetch_nba_schedule()

from typing import Set


import requests
from datetime import date

RAPIDAPI_HEADERS = {
    "x-rapidapi-key": "d4bfbc4596msh7f5df671e47c27dp1af307jsn849a11cfef2a",
    "x-rapidapi-host": "api-nba-v1.p.rapidapi.com",
}

def fetch_games_by_date(game_day: date):
    url = "https://api-nba-v1.p.rapidapi.com/games"
    querystring = {"date": game_day.isoformat()}
    resp = requests.get(url, headers=RAPIDAPI_HEADERS, params=querystring)
    resp.raise_for_status()
    # Rate limit between player fetches
    time.sleep(RATE_LIMIT_SECONDS)
    return resp.json()

def teams_playing_on(game_day: date, schedule: dict = None) -> Set[str]:
    """
    Return a set of team tricodes (e.g. 'MEM', 'LAL') that have a game on game_day.
    1) Prefer the local schedule JSON.
    2) If that returns nothing, fall back to the RapidAPI `games?date=YYYY-MM-DD`.
    """
    if schedule is None:
        schedule = SCHEDULE_DATA

    playing: Set[str] = set()
    league_sched = schedule.get("leagueSchedule", {})

    # --- 1) Try local JSON schedule ---
    for date_bucket in league_sched.get("gameDates", []):
        for game in date_bucket.get("games", []):
            game_utc = game.get("gameDateUTC")
            if not game_utc:
                continue

            try:
                game_date = datetime.fromisoformat(
                    game_utc.replace("Z", "+00:00")
                ).date()
            except ValueError:
                continue

            if game_date != game_day:
                continue

            home = game.get("homeTeam", {}) or {}
            away = game.get("awayTeam", {}) or {}

            home_tri = home.get("teamTricode")
            away_tri = away.get("teamTricode")

            if home_tri:
                playing.add(home_tri.upper())
            if away_tri:
                playing.add(away_tri.upper())

    if playing:
        print(f"[teams_playing_on] (local JSON) {game_day}: {sorted(playing)}")
        return playing

    # --- 2) Fallback: RapidAPI schedule for that date ---
    try:
        api_data = fetch_games_by_date(game_day)
        games = api_data.get("response", []) or []
        for g in games:
            teams = g.get("teams", {}) or {}
            home = teams.get("home", {}) or {}
            away = teams.get("visitors", {}) or {}  # note: 'visitors' in this API

            home_code = home.get("code")
            away_code = away.get("code")

            if home_code:
                playing.add(home_code.upper())
            if away_code:
                playing.add(away_code.upper())

        print(f"[teams_playing_on] (RapidAPI) {game_day}: {sorted(playing)}")
    except Exception as e:
        print(f"[teams_playing_on] RapidAPI fallback failed for {game_day}: {e}")

    return playing


def is_team_playing_on(team: str | None, game_day: date, schedule: dict = None) -> bool:
    team_can = canonical_team(team)
    if team_can is None:
        return False
    return team_can in teams_playing_on(game_day, schedule)



# Example usage
#print("yay")
#print(fetch_nba_playByplay('ad3128ea-6925-407c-a5a0-f04c12e25521'))
