import json
import random
import time
from datetime import date, timedelta

from fantasy import league
from nbaTest import is_team_playing_on  # we’ll keep using your helper


# ---- Shared helpers (copied from your other script so this is self-contained) ----

def load_history(path="fantasy_player_history_2025-26.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def player_fp_distribution(player, history_map):
    """
    Return list of fantasy scores for a single ESPN player.
    """
    pid_str = str(player.playerId)
    data = history_map.get(pid_str)
    if not data:
        return None

    hist = data.get("history", [])
    scores = [h["fantasy_points"] for h in hist if h.get("fantasy_points") is not None]
    return scores if scores else None


def is_player_active_on_day(player, game_day):
    """
    Determine if a player should count for a specific day:
    - Not on bench / IR
    - Not flagged as injured
    - Their NBA team has a game on that day
    """
    # Adjust slot names if your league uses slightly different codes
    if getattr(player, "lineupSlot", None) in ("BE", "IR", "IR+", "IL", "IL+"):
        return False
    if getattr(player, "injured", False):
        return False
    pro_team = getattr(player, "proTeam", None)
    if not is_team_playing_on(pro_team, game_day):
        return False
    return True


def team_score_for_day(team, history_map, game_day):
    """
    Simulate a SINGLE realization of this team’s score on a given day.
    """
    total = 0.0
    for p in team.roster:
        if not is_player_active_on_day(p, game_day):
            continue

        dist = player_fp_distribution(p, history_map)
        if not dist:
            continue

        total += random.choice(dist)
    return total


# ---- Week-level Monte Carlo ----

def date_range(start: date, end: date):
    """Inclusive date range generator."""
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def weekly_monte_carlo(team1,
                       team2,
                       history_map,
                       current_score_t1: float,
                       current_score_t2: float,
                       start_day: date,
                       end_day: date,
                       trials: int = 1000):
    """
    Simulate the rest of the week between start_day and end_day (inclusive)
    trials times, starting from the current scores.

    Returns a dict with win counts, probabilities, and average final totals.
    """
    t1_wins = 0
    t2_wins = 0
    ties = 0

    sum_t1 = 0.0
    sum_t2 = 0.0

    days = list(date_range(start_day, end_day))

    for _ in range(trials):
        total1 = current_score_t1
        total2 = current_score_t2

        for day in days:
            total1 += team_score_for_day(team1, history_map, day)
            total2 += team_score_for_day(team2, history_map, day)

        sum_t1 += total1
        sum_t2 += total2

        if total1 > total2:
            t1_wins += 1
        elif total2 > total1:
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
        "start_day": start_day,
        "end_day": end_day,
    }


# ---- Wire it up for Team Burnett vs DominAYTON ----

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

    TEAM_A_NAME = "LeBron's Lemmings"
    TEAM_B_NAME = "Sarr Fox 64"

    box = find_matchup_box(TEAM_A_NAME, TEAM_B_NAME)
    if box is None:
        raise RuntimeError(f"Could not find box score for {TEAM_A_NAME} vs {TEAM_B_NAME}")

    # Figure out which side is which in the box
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

    today = date.today()

    # ESPN H2H weeks are Monday–Sunday; adjust if your league differs
    week_start = today - timedelta(days=today.weekday())      # Monday
    week_end = week_start + timedelta(days=6)                 # Sunday

    # We only simulate from "today" forward
    simulate_from = max(today, week_start)

    print(f"Matchup: {TEAM_A_NAME} vs {TEAM_B_NAME}")
    print(f"Current score: {TEAM_A_NAME} {current_t1:.1f}  |  {TEAM_B_NAME} {current_t2:.1f}")
    print(f"Simulating days: {simulate_from} → {week_end}")

    start_ts = time.perf_counter()
    results = weekly_monte_carlo(
        team1=team1,
        team2=team2,
        history_map=history,
        current_score_t1=current_t1,
        current_score_t2=current_t2,
        start_day=simulate_from,
        end_day=week_end,
        trials=10000,   # bump up to e.g. 10000 if it runs fast enough
    )
    elapsed = time.perf_counter() - start_ts

    print("\n=======================================")
    print(f"Trials (full week simulations): {results['trials']}")
    print(f"Week span: {results['start_day']} → {results['end_day']}")
    print(f"Runtime: {elapsed:.2f} seconds")
    print()
    print(f"Average final {TEAM_A_NAME}: {results['avg_team1']:.1f}")
    print(f"Average final {TEAM_B_NAME}: {results['avg_team2']:.1f}")
    print()
    print(f"{TEAM_A_NAME} wins: {results['team1_wins']} "
          f"({results['p_team1']*100:.2f}%)")
    print(f"{TEAM_B_NAME} wins: {results['team2_wins']} "
          f"({results['p_team2']*100:.2f}%)")
    print(f"Ties: {results['ties']} "
          f"({results['p_tie']*100:.2f}%)")
    print("=======================================")
