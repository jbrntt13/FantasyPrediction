# weekly_sim.py

import json
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

    for _ in range(trials):
        s1, s2 = simulate_full_week_once(
            t1_entries_by_day,
            t2_entries_by_day,
            history_map,
        )

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


if __name__ == "__main__":
    hist = load_history()
    today = date.today()

    # Pick the matchup you care about.
    TEAM_A_NAME = "LeBron's Lemmings"
    TEAM_B_NAME = "DominAYTON"

    # Find the weekly box score / matchup so we can confirm teams
    box_scores = league.box_scores(matchup_total=True)

    target_box = None
    for box in box_scores:
        names = {box.home_team.team_name, box.away_team.team_name}
        if TEAM_A_NAME in names and TEAM_B_NAME in names:
            target_box = box
            break

    if target_box is None:
        raise RuntimeError(f"Could not find matchup {TEAM_A_NAME} vs {TEAM_B_NAME}")

    # Figure out which is team1 vs team2
    if target_box.home_team.team_name == TEAM_A_NAME:
        team1 = target_box.home_team
        team2 = target_box.away_team
        current_t1 = target_box.home_score
        current_t2 = target_box.away_score
    else:
        team1 = target_box.away_team
        team2 = target_box.home_team
        current_t1 = target_box.away_score
        current_t2 = target_box.home_score

    print(f"Matchup: {TEAM_A_NAME} vs {TEAM_B_NAME}")
    print(f"Current score (ESPN weekly): "
          f"{TEAM_A_NAME} {current_t1:.1f}  |  {TEAM_B_NAME} {current_t2:.1f}")

    week_start, week_end = week_bounds_from_today(today)
    print(f"\nWeek span: {week_start} → {week_end}")

    TRIALS = 10000
    results = monte_carlo_week(
        team1,
        team2,
        hist,
        start_day=week_start,
        end_day=week_end,
        trials=TRIALS,
    )

    print("\n=======================================")
    print(f"Trials (full week simulations): {results['trials']}")
    print(f"Week span: {week_start} → {week_end}")
    print()
    print(f"Average simulated {TEAM_A_NAME}: {results['avg_team1']:.1f}")
    print(f"Average simulated {TEAM_B_NAME}: {results['avg_team2']:.1f}")
    print()
    print(f"{TEAM_A_NAME} wins: {results['team1_wins']} "
          f"({results['p_team1']*100:.2f}%)")
    print(f"{TEAM_B_NAME} wins: {results['team2_wins']} "
          f"({results['p_team2']*100:.2f}%)")
    print(f"Ties: {results['ties']} "
          f"({results['p_tie']*100:.2f}%)")
    print("=======================================")
