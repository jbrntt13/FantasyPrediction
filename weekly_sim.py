# weekly_sim.py

import json
import time
from datetime import date, timedelta

from fantasy import league
from nbaTest import teams_playing_on
from simulate_matchup import (
    load_history,
    active_player_entries,
    team_score_once,
)


def week_bounds_from_today(today: date | None = None) -> tuple[date, date]:
    """
    Given 'today', return (monday, sunday) of the current fantasy week.
    Right now we just do calendar Monday–Sunday.
    If you later want to align to ESPN scoring periods, we can swap this out.
    """
    if today is None:
        today = date.today()

    # Monday = 0, Sunday = 6
    weekday = today.weekday()
    monday = today - timedelta(days=weekday)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def build_entries_for_range(team, history_map, start_day: date, end_day: date):
    """
    For each day in [start_day, end_day], precompute the list of (player, dist)
    for players who are:
      - in the active lineup
      - not injured
      - whose NBA team has a game that day
      - and who have historical fantasy data
    """
    entries_by_day: dict[date, list] = {}

    day = start_day
    while day <= end_day:
        playing_teams = teams_playing_on(day)

        print(f"\n[{day}] NBA teams playing: {sorted(playing_teams)}")

        entries = active_player_entries(
            team=team,
            history_map=history_map,
            game_day=day,
            playing_teams=playing_teams,
        )

        print(
            f"[{day}] Active players for {team.team_name}: "
            f"{len(entries)}"
        )
        for p, _dist in entries:
            print(f"    - {p.name} (proTeam={getattr(p, 'proTeam', None)})")

        entries_by_day[day] = entries
        day += timedelta(days=1)

    return entries_by_day


def simulate_full_week_once(
    team1_entries_by_day: dict[date, list],
    team2_entries_by_day: dict[date, list],
    history_map,
) -> tuple[float, float]:
    """
    One outer Monte Carlo sample:
      - For each day in the week, draw one score for each active player
        for that day and sum across the week.
    """
    t1_total = 0.0
    t2_total = 0.0

    for day in sorted(team1_entries_by_day.keys()):
        t1_entries = team1_entries_by_day[day]
        t2_entries = team2_entries_by_day[day]

        # If a team has no active players on a given day,
        # team_score_once will just return 0.
        t1_total += team_score_once(t1_entries, history_map)
        t2_total += team_score_once(t2_entries, history_map)

    return t1_total, t2_total


def monte_carlo_week(
    team1,
    team2,
    history_map,
    start_day: date,
    end_day: date,
    trials: int = 10000,
):
    """
    Outer Monte Carlo over full-week outcomes.
    """
    print(
        f"Simulating days: {start_day} → {end_day} "
        f"({(end_day - start_day).days + 1} days)"
    )

    # Precompute entries per day per team
    print(f"\n=== Precomputing active players for {team1.team_name} ===")
    t1_entries_by_day = build_entries_for_range(team1, history_map, start_day, end_day)

    print(f"\n=== Precomputing active players for {team2.team_name} ===")
    t2_entries_by_day = build_entries_for_range(team2, history_map, start_day, end_day)

    # Quick sanity check
    total_t1_players = sum(len(v) for v in t1_entries_by_day.values())
    total_t2_players = sum(len(v) for v in t2_entries_by_day.values())
    print(
        f"\nSummary of active player-days "
        f"({team1.team_name}: {total_t1_players}, "
        f"{team2.team_name}: {total_t2_players})"
    )

    t1_wins = t2_wins = ties = 0
    sum_t1 = sum_t2 = 0.0
    all_days = sorted(set(t1_entries_by_day.keys()) | set(t2_entries_by_day.keys()))
    day_sums_t1 = {d: 0.0 for d in all_days}
    day_sums_t2 = {d: 0.0 for d in all_days}

    for _ in range(trials):
        weekly_t1 = 0.0
        weekly_t2 = 0.0

        for day in all_days:
            t1_entries = t1_entries_by_day.get(day, [])
            t2_entries = t2_entries_by_day.get(day, [])
            s1_day = team_score_once(t1_entries, history_map)
            s2_day = team_score_once(t2_entries, history_map)
            weekly_t1 += s1_day
            weekly_t2 += s2_day
            day_sums_t1[day] += s1_day
            day_sums_t2[day] += s2_day

        sum_t1 += weekly_t1
        sum_t2 += weekly_t2

        if weekly_t1 > weekly_t2:
            t1_wins += 1
        elif weekly_t2 > weekly_t1:
            t2_wins += 1
        else:
            ties += 1

    avg_t1 = sum_t1 / trials
    avg_t2 = sum_t2 / trials

    daily_avgs = {
        d.isoformat(): {
            "team1": day_sums_t1[d] / trials,
            "team2": day_sums_t2[d] / trials,
        }
        for d in all_days
    }

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
        "daily_avgs": daily_avgs,
    }


def run_weekly_matchups(trials: int = 10000, save: bool = True):
    """
    Simulate weekly odds for all current matchups and return a dict with
    per-matchup odds and per-day projected scoring.
    """

    hist = load_history()
    today = date.today()
    week_start, week_end = week_bounds_from_today(today)

    results_list = []

    for box in league.box_scores(matchup_total=True):
        home_team = box.home_team
        away_team = box.away_team

        res = monte_carlo_week(
            home_team,
            away_team,
            hist,
            start_day=week_start,
            end_day=week_end,
            trials=trials,
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
            "daily_scores": res["daily_avgs"],
        })

    result = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "matchups": results_list,
        "runtime_seconds": round(time.time() - start_ts, 2),
    }

    if save:
        filename = f"{week_start.isoformat()}_weekly_odds.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"[run_weekly_matchups] saved weekly odds to {filename}")
        except OSError as exc:
            print(f"[run_weekly_matchups] could not write {filename}: {exc}")

    return result


if __name__ == "__main__":
    start_ts = time.time()
    data = run_weekly_matchups(trials=10000, save=True)
    print(f"Weekly simulations for {data['week_start']} → {data['week_end']}")
    for m in data["matchups"]:
        print("\n---------------------------------------")
        print(f"{m['home_team']} vs {m['away_team']}")
        print(f"Trials: {m['trials']}")
        print(f"Avg score {m['home_team']}: {m['home_avg']:.1f}")
        print(f"Avg score {m['away_team']}: {m['away_avg']:.1f}")
        print(f"{m['home_team']} win prob: {m['home_win_prob']*100:.2f}%")
        print(f"{m['away_team']} win prob: {m['away_win_prob']*100:.2f}%")
        print(f"Tie prob: {m['tie_prob']*100:.2f}%")
        print("Daily projected averages:")
        for day, scores in sorted(m["daily_scores"].items()):
            print(f"  {day}: {m['home_team']} {scores['team1']:.1f} | {m['away_team']} {scores['team2']:.1f}")

    runtime = round(time.time() - start_ts, 2)
    print(f"\nTotal runtime: {runtime}s")
