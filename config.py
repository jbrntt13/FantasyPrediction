"""
Central configuration for the FantasyPrediction backend.

Everything season- or credential-specific lives here so a new season only
requires changing environment variables (or a `.env` file) and dropping in
the new NBA schedule file.

Environment variables (see .env.example):
  ESPN_LEAGUE_ID   ESPN fantasy league id (default: 538595081)
  ESPN_YEAR        ESPN season key = the year the season ENDS (2026-27 -> 2027).
                   Defaults to the current season based on today's date.
  ESPN_S2          espn_s2 cookie (required for private leagues)
  ESPN_SWID        SWID cookie, including the curly braces
  CACHE_DIR        Where daily/weekly odds caches are written (default: ./cache)
"""

import os
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """Tiny .env loader: KEY=VALUE lines, '#' comments, no dependency needed.
    Real environment variables always win over the file."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BASE_DIR / ".env")


def _default_espn_year(today: date | None = None) -> int:
    """ESPN keys a season by the calendar year it ends in. The NBA season
    starts in October, so Oct-Dec map to next year, Jan-Sep to this year."""
    today = today or date.today()
    return today.year + 1 if today.month >= 10 else today.year


ESPN_LEAGUE_ID: int = int(os.environ.get("ESPN_LEAGUE_ID", "538595081"))
ESPN_YEAR: int = int(os.environ.get("ESPN_YEAR") or _default_espn_year())
ESPN_S2: str | None = os.environ.get("ESPN_S2") or None
ESPN_SWID: str | None = os.environ.get("ESPN_SWID") or None

# nba_api season string, e.g. ESPN_YEAR=2027 -> "2026-27"
NBA_SEASON: str = f"{ESPN_YEAR - 1}-{str(ESPN_YEAR)[-2:]}"

DATA_DIR: Path = BASE_DIR / "data"
CACHE_DIR: Path = Path(os.environ.get("CACHE_DIR") or (BASE_DIR / "cache"))

# Per-season input files. Drop the new season's files in ./data with these names.
SCHEDULE_PATH: Path = DATA_DIR / f"scheduleLeagueV2_{NBA_SEASON}.json"
HISTORY_PATH: Path = DATA_DIR / f"fantasy_player_history_{NBA_SEASON}.json"


def proj_score_cache(day: date) -> Path:
    """Cache file for one day's simulated matchups."""
    return CACHE_DIR / f"{day.isoformat()}_projScore.json"


def weekly_odds_cache(week_start: date) -> Path:
    """Cache file for one fantasy week's simulated odds."""
    return CACHE_DIR / f"{week_start.isoformat()}_weekly_odds.json"


def describe() -> str:
    return (
        f"league={ESPN_LEAGUE_ID} espn_year={ESPN_YEAR} nba_season={NBA_SEASON} "
        f"creds={'set' if (ESPN_S2 and ESPN_SWID) else 'MISSING'} "
        f"schedule={SCHEDULE_PATH.name} history={HISTORY_PATH.name} cache={CACHE_DIR}"
    )
