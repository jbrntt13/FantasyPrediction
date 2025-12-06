# live_odds.py

import json
import random
from datetime import date
from pathlib import Path
from typing import Dict, Any

from nba_api.stats.endpoints import ScoreboardV2, BoxScoreTraditionalV2

from fantasy import league  # your ESPN league object


# -----------------------------
# History loading / distribution
# -----------------------------

HISTORY_PATH = Path("fantasy_player_history_2025-26.json")


def load_history(path: Path = HISTORY_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def player_fp_distribution(player, history_map: Dict[str, Any]):
    """
    Return list of full-game fantasy scores for a single ESPN player.
    """
    pid = str(player.playerId)
    data = history_map.get(pid)
    if not data:
        return None

    hist = data.get("history", [])
    scores = [
        h["fantasy_points"]
        for h in hist
        if h.get("fantasy_points") is not None
    ]
    return scores if scores else None


# -----------------------------
# NBA scoreboard / live status
# -----------------------------

def get_today_scoreboard(game_day: date | None = None):
    """
    Use nba_api ScoreboardV2 to get today’s games + team line scores.
    """
    if game_day is None:
        game_day = date.today()

    game_date_str = game_day.strftime("%m/%d/%Y")

    sb = ScoreboardV2(game_date=game_date_str, league_id="00", day_offset=0)
    games_df = sb.game_header.get_data_frame()
    line_scores_df = sb.line_score.get_data_frame()
    return games_df, line_scores_df


def build_team_to_game_map(game_day: date | None = None):
    """
    Map NBA team abbreviation (e.g. 'PHX') -> GAME_ID for today.
    """
    games_df, line_scores_df = get_today_scoreboard(game_day)

    team_to_game: Dict[str, str] = {}
    for _, row in line_scores_df.iterrows():
        team_abbr = row["TEAM_ABBREVIATION"]  # e.g. 'PHX'
        game_id = row["GAME_ID"]
        team_to_game[team_abbr] = game_id

    return team_to_game, games_df


def get_game_row(games_df, game_id: str):
    row = games_df[games_df["GAME_ID"] == game_id]
    if row.empty:
        return None
    return row.iloc[0]


def game_fraction_done(game_row) -> float:
    """
    Estimate how much of the game is completed (0.0–1.0) from ScoreboardV2 game_header row.
    """
    status = game_row["GAME_STATUS_ID"]

    # 1 = not started, 2 = in progress, 3 = final
    if status == 1:
        return 0.0
    if status == 3:
        return 1.0

    # In progress
    period = game_row.get("LIVE_PERIOD", game_row.get("PERIOD", 1))
    clock_str = game_row.get("LIVE_PC_TIME", "")

    total_minutes = 48.0  # regulation game: 4 * 12

    # If clock info is missing, rough guess: mid-period
    if not clock_str or not isinstance(clock_str, str) or ":" not in clock_str:
        minutes_elapsed = (period - 1) * 12 + 6
        frac = minutes_elapsed / total_minutes
        return max(0.0, min(1.0, frac))

    try:
        mins_left, secs_left = map(int, clock_str.split(":"))
        minutes_left_in_period = mins_left + secs_left / 60.0
    except Exception:
        minutes_left_in_period = 6.0

    minutes_elapsed = (period - 1) * 12 + (12.0 - minutes_left_in_period)
    frac = minutes_elapsed / total_minutes
    return max(0.0, min(1.0, frac))


def player_has_game_today(player, team_to_game_map: Dict[str, str]) -> bool:
    pro_team = getattr(player, "proTeam", None)
    if not pro_team:
        return False
    return pro_team in team_to_game_map


# -----------------------------
# Boxscore → fantasy points
# -----------------------------

def get_player_partial_boxscore(game_id: str, nba_player_id: int):
    """
    Fetch the partial boxscore row for a given player in a given game.
    """
    box = BoxScoreTraditionalV2(game_id=game_id)
    stats_df = box.player_stats.get_data_frame()
    row = stats_df[stats_df["PLAYER_ID"] == nba_player_id]
    if row.empty:
        return None
    return row.iloc[0]


def compute_fantasy_from_stat_row(row) -> float:
    """
    Compute fantasy points from a BoxScoreTraditionalV2 row
    using your league’s scoring settings.
    """
    pts = row["PTS"]
    reb = row["REB"]
    ast = row["AST"]
    stl = row["STL"]
    blk = row["BLK"]
    tov = row["TOV"]
    fgm = row["FGM"]
    ftm = row["FTM"]
    fta = row["FTA"]
    tpm = row["FG3M"]

    # Compute double / triple / quad doubles based on 5 main counting stats
    cat_vals = [
        pts,
        reb,
        ast,
        stl,
        blk,
    ]
    double_cats = sum(1 for v in cat_vals if v >= 10)

    dd = 1 if double_cats >= 2 else 0
    td = 1 if double_cats >= 3 else 0
    qd = 1 if double_cats >= 4 else 0

    score = 0
    score += fgm * 2           # Field Goals Made (FGM) 2
    score += ftm * 1           # Free Throws Made (FTM) 1
    score += fta * -1          # Free Throws Attempted (FTA) -1
    score += tpm * 1           # Three Pointers Made (3PM) 1
    score += reb * 1           # Rebounds (REB) 1
    score += ast * 2           # Assists (AST) 2
    score += stl * 4           # Steals (STL) 4
    score += blk * 4           # Blocks (BLK) 4
    score += tov * -2          # Turnovers (TO) -2
    score += dd * 5            # Double Doubles (DD) 5
    score += td * 8            # Triple Doubles (TD) 8
    score += qd * 13           # Quadruple Doubles (QD) 13
    score += pts * 1           # Points (PTS) 1

    return float(score)


# -----------------------------
# Live state builder
# -----------------------------

def build_player_live_state(
    player,
    history_map: Dict[str, Any],
    team_to_game_map: Dict[str, str],
    games_df,
) -> Dict[str, Any] | None:
    """
    Return a per-player dict describing today's game status:

        {
          "has_game_today": True,
          "fraction_done": float,
          "fantasy_points_so_far": float
        }

    or None if the player has no game today.
    """
    pro_team = getattr(player, "proTeam", None)
    if not pro_team or pro_team not in team_to_game_map:
        return None

    game_id = team_to_game_map[pro_team]
    game_row = get_game_row(games_df, game_id)
    if game_row is None:
        return None

    frac = game_fraction_done(game_row)

    # Get nba_player_id from history JSON if we have it
    player_hist = history_map.get(str(player.playerId))
    if not player_hist:
        nba_id = None
    else:
        nba_id = player_hist.get("nba_player_id")

    if not nba_id:
        # We know the player has a game, but not how to map them to NBA stats → treat as 0 so far
        return {
            "has_game_today": True,
            "fraction_done": frac,
            "fantasy_points_so_far": 0.0,
        }

    partial_row = get_player_partial_boxscore(game_id, nba_id)
    if partial_row is None:
        fp_so_far = 0.0
    else:
        fp_so_far = compute_fantasy_from_stat_row(partial_row)

    return {
        "has_game_today": True,
        "fraction_done": frac,
        "fantasy_points_so_far": fp_so_far,
    }


def build_live_state_for_league(
    history_map: Dict[str, Any],
    game_day: date | None = None,
) -> Dict[int, Dict[str, Any]]:
    """
    Build live state for every fantasy player in the league for the given day.
    Returns: dict[espn_player_id] = { has_game_today, fraction_done, fantasy_points_so_far }
    """
    team_to_game, games_df = build_team_to_game_map(game_day)
    live_state: Dict[int, Dict[str, Any]] = {}

    for team in league.teams:
        for p in team.roster:
            state = build_player_live_state(p, history_map, team_to_game, games_df)
            if state is not None:
                live_state[p.playerId] = state

    return live_state


# -----------------------------
# Linear rest-of-game simulation
# -----------------------------

def simulate_player_tonight_linear(
    player,
    history_map: Dict[str, Any],
    live_state: Dict[int, Dict[str, Any]],
) -> float:
    """
    Simulate this player's final fantasy score for tonight,
    using the "linear scoring / return-to-mean for the rest of game" assumption.

    - If no game today → returns 0.0
    - If game not started → draws a full-game from history (same as before)
    - If game in progress → current points + (sampled_full_game * remaining_fraction)
    - If game finished → returns actual points_so_far (no randomness)
    """
    state = live_state.get(player.playerId)
    if not state or not state.get("has_game_today", False):
        return 0.0

    P_curr = float(state["fantasy_points_so_far"])
    f = float(state["fraction_done"])
    remaining_frac = max(0.0, 1.0 - f)

    # Game fully done → no more randomness
    if remaining_frac <= 0.0:
        return P_curr

    dist = player_fp_distribution(player, history_map)
    if not dist:
        # No historical data → assume they just finish with what they have now
        return P_curr

    # Sample a full-game score from historical distribution
    F = random.choice(dist)

    # Assume scoring is linear through the game:
    # rest-of-game points = F * fraction_of_game_remaining
    rest_points = F * remaining_frac

    return P_curr + rest_points


def team_live_score_today(team, history_map: Dict[str, Any], live_state: Dict[int, Dict[str, Any]]) -> float:
    """
    Sum simulated *tonight's* fantasy points for all players on this fantasy team.
    Only counts players with a game today.
    """
    total = 0.0
    for p in team.roster:
        total += simulate_player_tonight_linear(p, history_map, live_state)
    return total


# -----------------------------
# Live Monte Carlo for a matchup
# -----------------------------

def live_monte_carlo_matchup(
    team1,
    team2,
    history_map: Dict[str, Any],
    live_state: Dict[int, Dict[str, Any]],
    current_score_t1: float,
    current_score_t2: float,
    trials: int = 10000,
) -> Dict[str, Any]:
    """
    Run Monte Carlo for the rest-of-today based on live state.

    For each trial:
      - simulate tonight's final scores for all players on both teams
      - add to current matchup scores
      - compare totals
    """
    t1_wins = 0
    t2_wins = 0
    ties = 0

    sum_t1 = 0.0
    sum_t2 = 0.0

    for _ in range(trials):
        # Simulate tonight’s total for each team
        sim_today_t1 = team_live_score_today(team1, history_map, live_state)
        sim_today_t2 = team_live_score_today(team2, history_map, live_state)

        final_t1 = current_score_t1 + sim_today_t1
        final_t2 = current_score_t2 + sim_today_t2

        sum_t1 += final_t1
        sum_t2 += final_t2

        if final_t1 > final_t2:
            t1_wins += 1
        elif final_t2 > final_t1:
            t2_wins += 1
        else:
            ties += 1

    avg_t1 = sum_t1 / trials
    avg_t2 = sum_t2 / trials

    return {
        "team1_wins": t1_wins,
        "team2_wins": t2_wins,
        "ties": ties,
        "p_team1": t1_wins / trials,
        "p_team2": t2_wins / trials,
        "p_tie": ties / trials,
        "avg_team1": avg_t1,
        "avg_team2": avg_t2,
        "trials": trials,
    }


# -----------------------------
# Example CLI: Burnett vs DominAYTON live odds
# -----------------------------

def find_matchup_box(team_name_a: str, team_name_b: str):
    """
    Find the current box score object for a given pair of team names.
    """
    for box in league.box_scores(matchup_total=True):
        h = box.home_team.team_name
        a = box.away_team.team_name
        if {h, a} == {team_name_a, team_name_b}:
            return box
    return None


if __name__ == "__main__":
    history = load_history()

    TEAM_A_NAME = "Team Burnett"
    TEAM_B_NAME = "DominAYTON"

    box = find_matchup_box(TEAM_A_NAME, TEAM_B_NAME)
    if box is None:
        raise RuntimeError(f"Could not find box score for {TEAM_A_NAME} vs {TEAM_B_NAME}")

    # Figure out which is team1 vs team2 in our result
    if box.home_team.team_name == TEAM_A_NAME:
        team1 = box.home_team
        team2 = box.away_team
        current_t1 = box.home_score
        current_t2 = box.away_score
    else:
        team1 = box.away_team
        team2 = box.home_team
        current_t1 = box.away_score
        current_t2 = box.home_score

    print(f"Matchup: {TEAM_A_NAME} vs {TEAM_B_NAME}")
    print(f"Current score: {TEAM_A_NAME} {current_t1:.1f}  |  {TEAM_B_NAME} {current_t2:.1f}")

    # Build live state for all fantasy players (today only)
    live_state = build_live_state_for_league(history)

    results = live_monte_carlo_matchup(
        team1=team1,
        team2=team2,
        history_map=history,
        live_state=live_state,
        current_score_t1=current_t1,
        current_score_t2=current_t2,
        trials=10000,
    )

    print("\n=======================================")
    print(f"Trials (live rest-of-today sims): {results['trials']}")
    print()
    print(f"Avg final {TEAM_A_NAME}: {results['avg_team1']:.1f}")
    print(f"Avg final {TEAM_B_NAME}: {results['avg_team2']:.1f}")
    print()
    print(f"{TEAM_A_NAME} wins: {results['team1_wins']} "
          f"({results['p_team1']*100:.2f}%)")
    print(f"{TEAM_B_NAME} wins: {results['team2_wins']} "
          f"({results['p_team2']*100:.2f}%)")
    print(f"Ties: {results['ties']} "
          f"({results['p_tie']*100:.2f}%)")
    print("=======================================")
