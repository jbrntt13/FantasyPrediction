import requests
import os
import json
from datetime import datetime, date
from typing import Set, Optional


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


def teams_playing_on(game_day: date, schedule: dict = None) -> Set[str]:

    """
    Return a set of team tricodes (e.g. 'MEM', 'LAL') that have a game on game_day.
    game_day is a datetime.date.
    """
    if schedule is None:
        schedule = SCHEDULE_DATA

    playing = set()
    league_sched = schedule.get("leagueSchedule", {})

    for date_bucket in league_sched.get("gameDates", []):
        for game in date_bucket.get("games", []):
            # Example: "2025-10-02T04:00:00Z"
            game_utc = game.get("gameDateUTC")
            if not game_utc:
                continue

            try:
                # strip Z, parse as ISO, take the date portion
                game_date = datetime.fromisoformat(
                    game_utc.replace("Z", "+00:00")
                ).date()
            except ValueError:
                continue

            if game_date != game_day:
                continue

            home = game.get("homeTeam", {})
            away = game.get("awayTeam", {})

            home_tri = home.get("teamTricode")
            away_tri = away.get("teamTricode")

            if home_tri:
                playing.add(home_tri.upper())
            if away_tri:
                playing.add(away_tri.upper())

    return playing


def is_team_playing_on(pro_team: str, game_day: date, schedule: dict = None) -> bool:
    """
    Convenience: is this pro_team (tricode) playing on game_day?
    """
    if not pro_team:
        return False
    return pro_team.upper() in teams_playing_on(game_day, schedule)


# Example usage
print(fetch_nba_live_games())
print("yay")
#print(fetch_nba_playByplay('ad3128ea-6925-407c-a5a0-f04c12e25521'))
