# weekly_sim.py

import json
import time
from datetime import date, timedelta
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from fantasy import league
from nbaTest import teams_playing_on
from simulate_matchup import (
    load_history,
    active_player_entries,
    team_score_once,
    run_today_matchups,
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

        #print(f"\n[{day}] NBA teams playing: {sorted(playing_teams)}")

        entries = active_player_entries(
            team=team,
            history_map=history_map,
            game_day=day,
            playing_teams=playing_teams,
        )

        #print( f"[{day}] Active players for {team.team_name}: " f"{len(entries)}" )
        #for p, _dist in entries:
            #print(f"    - {p.name} (proTeam={getattr(p, 'proTeam', None)})")

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
    #print(f"\n=== Precomputing active players for {team1.team_name} ===")
    t1_entries_by_day = build_entries_for_range(team1, history_map, start_day, end_day)

    #print(f"\n=== Precomputing active players for {team2.team_name} ===")
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

LA = ZoneInfo("America/Los_Angeles")
def run_weekly_matchups(trials: int = 10000, save: bool = True):
    """
    Simulate weekly odds for all current matchups and return a dict with
    per-matchup odds and per-day projected scoring.
    """
    print("currentMatchupPeriod", league.currentMatchupPeriod)
    print("scoringPeriodId", league.scoringPeriodId)
    print("matchup_periods", league.settings.matchup_periods)
    start_ts = time.time()
    hist = load_history()
    # Use date (not datetime) for stable week key and cache naming
    today_dt = datetime.now(tz=ZoneInfo("UTC")).astimezone(LA)
    today_date = today_dt.date()
    week_start, week_end = week_bounds_from_today(today_date)
    week_start_str = week_start.strftime("%Y-%m-%d")
    # Align cache naming with daily simulate_matchup convention: YYYY-MM-DD_projScore.json
    cache_file = Path(f"{week_start_str}_weekly_odds.json")
    today_data = run_today_matchups(trials=trials)
    today_current_scores = today_data.get("current_scores", {}) if today_data else {}
    today_is_live = today_data.get("is_live") if today_data else None

    cached_proj_scores = None
    cached_win_probs = None
    cached_current_scores = None
    if cache_file.exists():
        try:
            with cache_file.open("r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_proj_scores = cached.get("proj_scores")

            cached_win_probs = cached.get("win_probs")
            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            print("Cache file name:", cache_file.name   )
            print(cached_win_probs) 
            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            cached_current_scores = cached.get("current_scores")
            # Backfill from matchups if top-level maps are missing or legacy formatted
            matchups_cached = cached.get("matchups", [])
            if (cached_proj_scores is None or cached_win_probs is None) and matchups_cached:
                proj_tmp = {}
                win_tmp = {}
                for m in matchups_cached:
                    home = m.get("home_team")
                    away = m.get("away_team")
                    if home:
                        proj_tmp[home] = m.get("home_avg")
                        win_tmp[home] = m.get("home_win_prob")
                    if away:
                        proj_tmp[away] = m.get("away_avg")
                        win_tmp[away] = m.get("away_win_prob")
                if cached_proj_scores is None:
                    cached_proj_scores = proj_tmp
                if cached_win_probs is None:
                    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                    print(win_tmp)
                    cached_win_probs = win_tmp
            print(f"[run_weekly_matchups] loaded cached weekly projections from {cache_file.name}")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[run_weekly_matchups] failed to read cached weekly projections: {exc}")

    if not today_current_scores and cached_current_scores:
        today_current_scores = cached_current_scores
    if today_is_live is None and cache_file.exists():
        try:
            with cache_file.open("r", encoding="utf-8") as f:
                cached = json.load(f)
            today_is_live = cached.get("is_live")
        except Exception:
            pass

    results_list = []

    for box in league.box_scores(matchup_total=True, matchup_period=league.currentMatchupPeriod):
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

        today_iso = today_dt.isoformat()
        home_current = today_current_scores.get(home_team.team_name)
        away_current = today_current_scores.get(away_team.team_name)
        if today_iso in res["daily_avgs"]:
            if home_current is not None:
                res["daily_avgs"][today_iso]["team1"] = home_current
            if away_current is not None:
                res["daily_avgs"][today_iso]["team2"] = away_current

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
            "home_current_score": home_current,
            "away_current_score": away_current,
        })

    proj_scores = {}
    win_probs = {}
    for m in results_list:
        proj_scores[m["home_team"]] = m["home_avg"]
        proj_scores[m["away_team"]] = m["away_avg"]
        win_probs[m["home_team"]] = m["home_win_prob"]
        win_probs[m["away_team"]] = m["away_win_prob"]

    if cached_proj_scores:
        proj_scores = cached_proj_scores
    if cached_win_probs:
        win_probs = cached_win_probs

    result = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "matchups": results_list,
        "proj_scores": proj_scores,
        "win_probs": win_probs,
        "current_scores": today_current_scores,
        "is_live": today_is_live,
        "date": today_dt.date().isoformat(),
        "runtime_seconds": round(time.time() - start_ts, 2),
    }

    if not cache_file.exists():
        filename = cache_file.name
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"[run_weekly_matchups] saved weekly odds to {filename}")
        except OSError as exc:
            print(f"[run_weekly_matchups] could not write {filename}: {exc}")
    elif save:
        print(f"[run_weekly_matchups] cache file already exists: {cache_file.name}")

    return result


if __name__ == "__main__":
    start_ts = time.time()
    data = run_weekly_matchups(trials=10000, save=True)
    proj_scores = data.get("proj_scores", {})
    win_probs = data.get("win_probs", {})
    print(f"Weekly simulations for {data['week_start']} → {data['week_end']}")
    for m in data["matchups"]:
        print("\n---------------------------------------")
        print(f"{m['home_team']} vs {m['away_team']}")
        print(f"Trials: {m['trials']}")
        print(f"Avg score {m['home_team']}: {m['home_avg']:.1f} (orig proj: {proj_scores.get(m['home_team'], 0):.1f})")
        print(f"Avg score {m['away_team']}: {m['away_avg']:.1f} (orig proj: {proj_scores.get(m['away_team'], 0):.1f})")
        print(f"{m['home_team']} win prob: {m['home_win_prob']*100:.2f}% (orig: {win_probs.get(m['home_team'], 0)*100:.2f}%)")
        print(f"{m['away_team']} win prob: {m['away_win_prob']*100:.2f}% (orig: {win_probs.get(m['away_team'], 0)*100:.2f}%)")
        print(f"Tie prob: {m['tie_prob']*100:.2f}%")
        print("Daily projected averages:")
        for day, scores in sorted(m["daily_scores"].items()):
            print(f"  {day}: {m['home_team']} {scores['team1']:.1f} | {m['away_team']} {scores['team2']:.1f}")

    runtime = round(time.time() - start_ts, 2)
    print(f"\nTotal runtime: {runtime}s (cached calc: {data.get('runtime_seconds', 'N/A')}s)")
