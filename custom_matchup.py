import json
import random
from datetime import date

from fantasy import league
from nbaTest import teams_playing_on
from live_odds import build_live_state_for_league, simulate_player_tonight_linear



def monte_carlo(team1, team2, history_map, trials=50000, game_day=None, live_state=None):
    if game_day is None:
        game_day = date.today()

    playing_teams = teams_playing_on(game_day)

    team1_entries = active_player_entries(team1, history_map, game_day, playing_teams)
    team2_entries = active_player_entries(team2, history_map, game_day, playing_teams)

    t1_wins = t2_wins = ties = 0
    sum_t1 = sum_t2 = 0.0

    for _ in range(trials):
        s1 = team_score_once(team1_entries, history_map, live_state=live_state)
        s2 = team_score_once(team2_entries, history_map, live_state=live_state)

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
