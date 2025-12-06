import json
import random
from datetime import date

from fantasy import league  # your ESPN league object
from nbaTest import is_team_playing_on, teams_playing_on


def load_history(path="fantasy_player_history_2025-26.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def player_fp_distribution(player, history_map):
    """
    Return list of fantasy scores for a single ESPN player.
    """
    pid = player.playerId
    if str(pid) not in history_map:
        return None  # missing player — ignore for now

    hist = history_map[str(pid)]["history"]
    return [h["fantasy_points"] for h in hist if h["fantasy_points"] is not None]





def is_player_active(player, game_day, playing_teams=None):
    """
    Determine if a player should count for today's simulation:
    - Not on bench/IR
    - Not flagged as injured
    - Their NBA team has a game on the given day
    """
    if player.lineupSlot in ("BE", "IR"):
        return False
    if getattr(player, "injured", False):
        return False
    pro_team = getattr(player, "proTeam", None)
    if playing_teams is not None:
        return pro_team in playing_teams
    return is_team_playing_on(pro_team, game_day)


def active_player_distributions(team, history_map, game_day, playing_teams):
    """
    Build the list of distributions once per matchup; lineup won't change mid-sim.
    """
    dists = []
    for p in team.roster:
        if not is_player_active(p, game_day, playing_teams):
            continue
        dist = player_fp_distribution(p, history_map)
        if dist:
            dists.append(dist)
    return dists


def team_score_once(player_dists):
    total = 0
    for dist in player_dists:
        total += random.choice(dist)
    return total


def monte_carlo(team1, team2, history_map, trials=50000, game_day=None):
    if game_day is None:
        game_day = date.today()

    # Precompute which NBA teams have a game to avoid repeated schedule lookups
    playing_teams = teams_playing_on(game_day)

    # Filter the lineups and precompute distributions once
    team1_dists = active_player_distributions(team1, history_map, game_day, playing_teams)
    team2_dists = active_player_distributions(team2, history_map, game_day, playing_teams)

    t1_wins = 0
    t2_wins = 0
    ties = 0

    sum_t1 = 0.0
    sum_t2 = 0.0

    for _ in range(trials):
        s1 = team_score_once(team1_dists)
        s2 = team_score_once(team2_dists)

        sum_t1 += s1
        sum_t2 += s2

        if s1 > s2:
            t1_wins += 1
        elif s2 > s1:
            t2_wins += 1
        else:
            ties += 1

    avg_t1 = sum_t1 / trials
    avg_t2 = sum_t2 / trials

    # probabilities
    p_t1 = t1_wins / trials
    p_t2 = t2_wins / trials
    p_tie = ties / trials

    return {
        "team1_wins": t1_wins,
        "team2_wins": t2_wins,
        "ties": ties,
        "p_team1": p_t1,
        "p_team2": p_t2,
        "p_tie": p_tie,
        "avg_team1": avg_t1,
        "avg_team2": avg_t2,
        "trials": trials,
    }



if __name__ == "__main__":
    hist = load_history()
    today = date.today()

    print(f"Simulating today's matchups ({today})...")
    box_scores = league.box_scores(matchup_total=False)

    for box in box_scores:
        home_team = box.home_team
        away_team = box.away_team

        print("\n---------------------------------------")
        print(f"{home_team.team_name} vs {away_team.team_name}")

        results = monte_carlo(home_team, away_team, hist, trials=20000, game_day=today)

        print(f"Trials: {results['trials']}")
        print(f"Simulated avg {home_team.team_name}: {results['avg_team1']:.1f}")
        print(f"Simulated avg {away_team.team_name}: {results['avg_team2']:.1f}")
        print(f"{home_team.team_name} wins: {results['team1_wins']} "
              f"({results['p_team1']*100:.2f}%)")
        print(f"{away_team.team_name} wins: {results['team2_wins']} "
              f"({results['p_team2']*100:.2f}%)")
        print(f"Ties: {results['ties']} "
              f"({results['p_tie']*100:.2f}%)")
