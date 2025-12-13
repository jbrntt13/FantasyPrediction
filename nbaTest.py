import os
import json
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Set, Optional, Union

from nba_api.live.nba.endpoints import scoreboard as live_scoreboard


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


def canonical_team(code: Optional[str]) -> Optional[str]:
    if code is None:
        return None
    return TEAM_CODE_CANON.get(code.upper(), code.upper())


def _la_today() -> date:
    """Today's date in America/Los_Angeles as a `date`."""
    la_tz = ZoneInfo("America/Los_Angeles")
    return datetime.now(tz=ZoneInfo("UTC")).astimezone(la_tz).date()


# ---------------------------------------------------------------------------
# Live games via nba_api.live scoreboard
# ---------------------------------------------------------------------------

def fetch_nba_live_games() -> dict:
    """
    Use nba_api.live.nba.endpoints.scoreboard.ScoreBoard to get today's games.

    We normalize this into a shape that matches what your old Basketball API
    code expected:

        {
          "response": [
            {
              "gameId": "...",
              "gameStatus": ...,
              "gameStatusText": "...",
              "teams": {
                "home": {"code": "MEM"},
                "visitors": {"code": "UTA"},
              },
            },
            ...
          ]
        }
    """
    games = live_scoreboard.ScoreBoard()
    data = games.get_dict()

    response = []
    for g in data.get("scoreboard", {}).get("games", []):
        home = g.get("homeTeam", {}) or {}
        away = g.get("awayTeam", {}) or {}

        home_code = home.get("teamTricode")
        away_code = away.get("teamTricode")

        response.append(
            {
                "gameId": g.get("gameId"),
                "gameStatus": g.get("gameStatus"),
                "gameStatusText": g.get("gameStatusText"),
                "teams": {
                    "home": {"code": home_code},
                    "visitors": {"code": away_code},
                },
            }
        )

    return {"response": response}


# ---------------------------------------------------------------------------
# Local schedule JSON
# ---------------------------------------------------------------------------

def fetch_nba_schedule(path: str | None = None) -> dict:
    """
    Load the full NBA schedule from a local JSON file instead of any HTTP API.
    Default: scheduleLeagueV2.json in the same directory as this file.
    """
    if path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "scheduleLeagueV2.json")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[fetch_nba_schedule] loaded schedule from {path}")
    return data


# Load once at module import
SCHEDULE_DATA = fetch_nba_schedule()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def teams_playing_on(
    game_day: Union[date, datetime],
    schedule: Optional[dict] = None
) -> Set[str]:
    """
    Return a set of team tricodes (e.g. 'MEM', 'LAL') that have a game on game_day.

    1) Prefer the local schedule JSON.
    2) If that returns nothing, fall back to the nba_api.live ScoreBoard for *today*.

    NOTE: If you pass a datetime, it will be converted to .date() so timezones
    don't silently break equality checks.
    """
    # Normalize datetime -> date so 2025-12-12T16:08 in LA matches the schedule
    if isinstance(game_day, datetime):
        game_day = game_day.date()

    if schedule is None:
        schedule = SCHEDULE_DATA

    playing: Set[str] = set()
    league_sched = schedule.get("leagueSchedule", {})

    # --- 1) Try local JSON schedule ---
    for date_bucket in league_sched.get("gameDates", []):
        for game in date_bucket.get("games", []):
            # You chose EST before because UTC in this file had some weird edge cases.
            game_utc = game.get("gameDateEST") or game.get("gameDateUTC") or ""
            if not game_utc:
                continue

            try:
                # gameDateEST looks like "2025-12-12T00:00:00Z"
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

    # --- 2) Fallback: live ScoreBoard for today's games ---
    try:
        today_la = _la_today()
        if game_day != today_la:
            print(
                f"[teams_playing_on] no schedule for {game_day}, "
                f"and live scoreboard is only for {today_la}; skipping fallback."
            )
            return playing

        api_data = fetch_nba_live_games()
        games = api_data.get("response", []) or []

        for g in games:
            teams = g.get("teams", {}) or {}
            home = teams.get("home", {}) or {}
            away = teams.get("visitors", {}) or {}

            home_code = home.get("code")
            away_code = away.get("code")

            if home_code:
                playing.add(canonical_team(home_code))
            if away_code:
                playing.add(canonical_team(away_code))

        print(f"[teams_playing_on] (live scoreboard) {game_day}: {sorted(playing)}")
    except Exception as e:
        print(f"[teams_playing_on] live scoreboard fallback failed for {game_day}: {e}")

    return playing


def is_team_playing_on(
    team: Optional[str],
    game_day: Union[date, datetime],
    schedule: Optional[dict] = None
) -> bool:
    team_can = canonical_team(team)
    if team_can is None:
        return False
    return team_can in teams_playing_on(game_day, schedule)
