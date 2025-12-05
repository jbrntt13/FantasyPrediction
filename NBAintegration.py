# nba_integration.py

from nba_api.stats.static import players as static_players
from nba_api.stats.endpoints import playergamelog
import pandas as pd
from datetime import datetime, timedelta, date

def current_nba_season_str() -> str:
    """
    Return the current NBA season string in 'YYYY-YY' form.
    Example:
      - Nov 2025 -> '2025-26'
      - Mar 2026 -> '2025-26'
      - Jun 2026 -> '2025-26'
      - Sep 2026 -> '2025-26' (still offseason, but season '2025-26' is the last)
    """
    today = date.today()
    year = today.year
    # NBA season "starts" in Oct; before that, we're still in last season
    if today.month >= 10:
        start = year
    else:
        start = year - 1
    end_short = str(start + 1)[-2:]
    return f"{start}-{end_short}"


# Scoring weights – your league rules
SCORING_RULES = {
    "FGM": 2,
    "FTM": 1,
    "FTA": -1,
    "FG3M": 1,   # 3PM
    "REB": 1,
    "AST": 2,
    "STL": 4,
    "BLK": 4,
    "TOV": -2,   # Turnovers
    "PTS": 1,
    # DD/TD/QD handled separately
}


def _count_double_double_categories(pts: float, reb: float, ast: float, stl: float, blk: float) -> int:
    """
    Count how many stat categories are >= 10 among PTS, REB, AST, STL, BLK.
    """
    cats = [pts, reb, ast, stl, blk]
    return sum(1 for v in cats if v >= 10)


def _dd_td_qd_bonus(pts: float, reb: float, ast: float, stl: float, blk: float) -> float:
    """
    Compute DD/TD/QD bonus points.

    Assumes stacking:
      - Double-double: 5
      - Triple-double: +8 (on top of DD)
      - Quadruple-double: +13 (on top of DD+TD)

    So a triple-double yields 13 total bonus,
    a quadruple-double yields 26 total bonus.
    """
    n = _count_double_double_categories(pts, reb, ast, stl, blk)

    bonus = 0.0
    if n >= 2:
        bonus += 5.0  # DD
    if n >= 3:
        bonus += 8.0  # TD
    if n >= 4:
        bonus += 13.0  # QD
    return bonus


def calc_fantasy_points_from_row(row) -> float:
    """
    Calculate fantasy points for a single game using your league's scoring.

    'row' can be:
      - a pandas.Series from nba_api PlayerGameLog,
      - or any dict-like with keys:
        FGM, FTM, FTA, FG3M, REB, AST, STL, BLK, TOV, PTS
    """
    # Safely pull stats, default to 0 if missing
    def g(key):
        if hasattr(row, "get"):
            return row.get(key, 0)  # works for dict-like / Series
        return row[key] if key in row else 0

    fgm = float(g("FGM"))
    ftm = float(g("FTM"))
    fta = float(g("FTA"))
    fg3m = float(g("FG3M"))  # 3PM
    reb = float(g("REB"))
    ast = float(g("AST"))
    stl = float(g("STL"))
    blk = float(g("BLK"))
    tov = float(g("TOV"))
    pts = float(g("PTS"))

    # Base scoring
    total = 0.0
    total += SCORING_RULES["FGM"] * fgm
    total += SCORING_RULES["FTM"] * ftm
    total += SCORING_RULES["FTA"] * fta
    total += SCORING_RULES["FG3M"] * fg3m
    total += SCORING_RULES["REB"] * reb
    total += SCORING_RULES["AST"] * ast
    total += SCORING_RULES["STL"] * stl
    total += SCORING_RULES["BLK"] * blk
    total += SCORING_RULES["TOV"] * tov
    total += SCORING_RULES["PTS"] * pts

    # Double/Triple/Quad bonuses
    total += _dd_td_qd_bonus(pts, reb, ast, stl, blk)

    return total


def find_nba_player_id(full_name: str):
    """
    Look up an NBA.com player ID by full name using nba_api's static players list.
    Returns the ID (int) or None if not found.
    """
    all_players = static_players.get_players()  # list of dicts
    full_name_lower = full_name.lower()

    # Exact full-name match first
    for p in all_players:
        if p["full_name"].lower() == full_name_lower:
            return p["id"]

    # Fallback: loose match (in case ESPN name formatting is slightly different)
    for p in all_players:
        if full_name_lower in p["full_name"].lower():
            return p["id"]

    return None


def get_nba_game_logs(nba_player_id: int, season: str = "2025-26") -> pd.DataFrame:
    gl = playergamelog.PlayerGameLog(
        player_id=nba_player_id,
        season=season,
        season_type_all_star="Regular Season",
    )
    df = gl.get_data_frames()[0]
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], format="%b %d, %Y")

    print(df.columns)  # <-- add this once to inspect

    return df



def build_fantasy_history_for_player(nba_player_id: int, season: str = "2025-26"):
    """
    Use nba_api logs + your scoring to build a history of fantasy points.

    Returns a list of dicts:
      { "date": date, "fantasy_points": float, "opponent": str, "game_id": str | None }
    """
    df = get_nba_game_logs(nba_player_id, season=season)
    history = []

    for _, row in df.iterrows():
        game_date = row["GAME_DATE"].date()
        fantasy_pts = calc_fantasy_points_from_row(row)

        # handle both possible casings just in case
        if hasattr(row, "get"):
            game_id = row.get("GAME_ID", row.get("Game_ID", None))
        else:
            # fallback if it's some other dict-like
            game_id = row["GAME_ID"] if "GAME_ID" in row else row.get("Game_ID")

        history.append({
            "date": game_date,
            "fantasy_points": fantasy_pts,
            "opponent": row["MATCHUP"],   # e.g. "UTA vs LAL"
            "game_id": game_id,
        })

    return history
