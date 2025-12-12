import json
import random
from datetime import date
from pathlib import Path

from fantasy import league
from nbaTest import teams_playing_on
from live_odds import build_live_state_for_league, simulate_player_tonight_linear
from datetime import datetime
from zoneinfo import ZoneInfo

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
    return teams_playing_on(pro_team, game_day)


def active_player_entries(team, history_map, game_day, playing_teams):
    """
    Return list of (player, dist) for active players with history.
    """
    entries = []
    for p in team.roster:
        if not is_player_active(p, game_day, playing_teams):
            continue
        dist = player_fp_distribution(p, history_map)
        if dist:
            entries.append((p, dist))
    return entries

def team_score_once(player_entries, history_map, live_state=None):
    """
    If live_state has an entry for this player, use live projection.
    Otherwise, sample from full-game history.
    """
    total = 0.0
    for player, dist in player_entries:
        if live_state is not None and player.playerId in live_state:
            total += simulate_player_tonight_linear(player, history_map, live_state)
        else:
            total += random.choice(dist)
    return total



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
LA = ZoneInfo("America/Los_Angeles")


def run_today_matchups(trials: int = 20000):
    """
    Runs Monte Carlo for all today's matchups and returns a list of dicts
    we can easily JSON-ify. If there are no live NBA games, persist the
    projected scores to a dated JSON file.
    """
    hist = load_history()
    today = datetime.now(tz=ZoneInfo("UTC")).astimezone(LA)
    date_str = today.date().isoformat()
    proj_file = Path(f"{date_str}_projScore.json")
    cached_proj_scores = None
    cached_win_probs = None
    if proj_file.exists():
        try:
            with proj_file.open("r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_proj_scores = cached.get("proj_scores")
            cached_win_probs = cached.get("win_probs")
            print(f"[run_today_matchups] loaded cached projections from {proj_file.name}")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[run_today_matchups] failed to read cached projections: {exc}")

    live_state = build_live_state_for_league(hist, game_day=today)
    is_live = bool(live_state)  # live_state populated only when there are active games
    box_scores = league.box_scores(matchup_total=False)

    results_list = []
    current_scores = {}

    for box in box_scores:
        home_team = box.home_team
        away_team = box.away_team
        home_current = box.home_score
        away_current = box.away_score

        res = monte_carlo(
            home_team,
            away_team,
            hist,
            trials=trials,
            game_day=today,
            live_state=live_state,
        )

        results_list.append({
            "home_team": home_team.team_name,
            "away_team": away_team.team_name,
            "home_avg": res["avg_team1"],
            "away_avg": res["avg_team2"],
            "home_win_prob": res["p_team1"],
            "away_win_prob": res["p_team2"],
            "tie_prob": res["p_tie"],
            "trials": res["trials"],
            "home_team_url": home_team.logo_url,
            "away_team_url": away_team.logo_url,
            "home_current_score": home_current,
            "away_current_score": away_current,
        })

    proj_scores = {}
    win_probs = {}
    for m in results_list:
        proj_scores[m["home_team"]] = m["home_avg"]
        proj_scores[m["away_team"]] = m["away_avg"]
        current_scores[m["home_team"]] = m["home_current_score"]
        current_scores[m["away_team"]] = m["away_current_score"]
        win_probs[m["home_team"]] = m["home_win_prob"]
        win_probs[m["away_team"]] = m["away_win_prob"]

    if cached_proj_scores:
        proj_scores = cached_proj_scores
    if cached_win_probs:
        win_probs = cached_win_probs

    result = {
        "date": date_str,
        "is_live": is_live,
        "matchups": results_list,
        "proj_scores": proj_scores,
        "current_scores": current_scores,
        "win_probs": win_probs,
    }

    if not is_live:
        filename = proj_file.name
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"[run_today_matchups] projected scores saved to {filename}")
        except OSError as exc:
            print(f"[run_today_matchups] could not write {filename}: {exc}")

    return result


def run_custom_matchup(team1_name: str, team2_name: str, trials: int = 20000):
    """
    Runs Monte Carlo for a specific pair of fantasy teams by name.
    """
    hist = load_history()
    today = date.today()
    live_state = build_live_state_for_league(hist, game_day=today)

    def find_team(name: str):
        for t in league.teams:
            if t.team_name.lower() == name.lower():
                return t
        return None

    team1 = find_team(team1_name)
    team2 = find_team(team2_name)

    if team1 is None or team2 is None:
        missing = [name for name, team in ((team1_name, team1), (team2_name, team2)) if team is None]
        raise ValueError(f"Team(s) not found: {', '.join(missing)}")

    res = monte_carlo(
        team1,
        team2,
        hist,
        trials=trials,
        game_day=today,
        live_state=live_state,
    )

    return {
        "team1": team1.team_name,
        "team2": team2.team_name,
        "team1_win_prob": res["p_team1"],
        "team2_win_prob": res["p_team2"],
        "tie_prob": res["p_tie"],
        "team1_avg": res["avg_team1"],
        "team2_avg": res["avg_team2"],
        "trials": res["trials"],
        "team1_url": team1.logo_url,
        "team2_url": team2.logo_url,
        "date": today.isoformat(),
    }


if __name__ == "__main__":
    data = run_today_matchups(trials=20000)

    print(f"Simulating today's matchups ({data['date']})...")

    for m in data["matchups"]:
        print("\n---------------------------------------")
        print(f"{m['home_team']} vs {m['away_team']}")
        print(f"Trials: {m['trials']}")
        print(f"Sim avg {m['home_team']}: {m['home_avg']:.1f}")
        print(f"Sim avg {m['away_team']}: {m['away_avg']:.1f}")
        print(f"{m['home_team']} win prob: {m['home_win_prob']*100:.2f}%")
        print(f"{m['away_team']} win prob: {m['away_win_prob']*100:.2f}%")
        print(f"Tie prob: {m['tie_prob']*100:.2f}%")
