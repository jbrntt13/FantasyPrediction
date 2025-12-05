# NBA Import
from datetime import datetime, timedelta, date
import scipy.stats as stats

import sys
from typing import List
from nbaTest import fetch_nba_live_games, is_team_playing_on
from datetime import datetime, timedelta, date

# Add the directory containing the espn_api module to the Python path
sys.path.append('A:\espn-api\espn-api')
#This is not an API FROM ESPN, this is an API for Fantasy from SPN
from espn_api.basketball import League, Matchup, Player, Team

league = League(league_id=538595081, year=2026,
                espn_s2='AECrq3n2a056zbwdJi7Cny73%2BlS0gpyt0BzVNowetvcsdgI%2BAZ5d7o90xOhnooEGoPQu95%2BVCj%2Fsdb3EELbdXuLiA1YHzrAonEIP1TLLVlES4KPHh4jdDZ9bcddu4k0sALh7QipurlQVUgJsLc8WT%2BkKpFIacloHpGxbtK%2BVPoowAqPH3YlEpxL2S6Ca9Nqqzml9QvUlNmvYL4iky%2F4G735Mf3yVor3Et%2FGgbrvSwfOfh370S6FV9c5nZZjzcCfpFiZbpZVQdmFpVQsgXipWnn9q0wUapcojXArHPDJyD02YYQ%3D%3D',
                swid='{F3126586-12DD-4281-9D5B-515865B5FC66}')
team = league.teams[1]

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

standard_point_deviation = 75
time_decay = 0.5

@app.route("/date")
def hello_world():
    box = league.box_scores(matchup_total=False)
    html = box[0].away_lineup[0]

    test = simplePrediction(615, 621)
    date = datetime.now().timestamp()
    print(html)
    return html



@app.route("/weeklyblindprojections")
def weeklyblindprojections():
    box = league.box_scores(matchup_total=False)
    projections = []
    nbaDATA = fetch_nba_live_games()

    for boxscore in box_scores:
        home_team_name = boxscore.home_team.team_name
        away_team_name = boxscore.away_team.team_name
        home_team_projected_points = 0
        away_team_projected_points = 0

        today = datetime.now().date()
        days_until_monday = (7 - today.weekday()) % 7  #We should do this outside of the boxscore loop ideally
        if days_until_monday == 0:
            days_until_monday = 7

        for i in range(days_until_monday):
            current_date = today + timedelta(days=i)
            print(current_date)
            home_team_projected_points += teamProjectScore(boxscore.home_lineup, boxscore.home_team.team_name, nbaDATA,
                                                           current_date)
            away_team_projected_points += teamProjectScore(boxscore.away_lineup, boxscore.away_team.team_name, nbaDATA,
                                                           current_date)
            #We're not done yet, we need to add the points already scored today
        currentBoxScore = league.box_scores()
        home_team_projected_points += currentBoxScore[0].home_score
        away_team_projected_points += currentBoxScore[0].away_score
        chanceHome, chanceAway = simplePrediction(home_team_projected_points, away_team_projected_points)

        projections.append((home_team_name, home_team_projected_points, chanceHome, away_team_name,
                            away_team_projected_points, chanceAway))

    print(projections)
    return projections


@app.route("/currentodds")
def currentOdds():
    box = league.box_scores(matchup_total=False)
    projections = []
    nbaDATA = fetch_nba_live_games()
    for boxscore in box:
        home_team_name = boxscore.home_team.team_name
        away_team_name = boxscore.away_team.team_name

        home_team_projected_points, homeFirstGame, homeLastGame = teamProjectScore(boxscore.home_lineup, boxscore.home_team.team_name, nbaDATA, datetime.now().date())


        away_team_projected_points, awayFirstGame, awayLastGame = teamProjectScore(boxscore.away_lineup, boxscore.away_team.team_name, nbaDATA,
                                                      datetime.now().date())

        chanceHome, chanceAway = simplePrediction(home_team_projected_points, away_team_projected_points, homeFirstGame, homeLastGame, awayFirstGame, awayLastGame)
        print(home_team_name, home_team_projected_points, (chanceHome * 100))
        print(away_team_name, away_team_projected_points, (chanceAway * 100))
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        projections.append((home_team_name, home_team_projected_points, chanceHome, away_team_name,
                            away_team_projected_points, chanceAway))
    #print(projections)
    return projections


@app.route("/testAPI")
def testAPI():
    fetch_nba_live_games()
    return "Hello, World!"





def simplePrediction(home_team: int, away_team: int, homeFirstGame: int, homelastGame: int, awayFirstGame: int, awayLastGame: int):
    difference = abs(home_team - away_team)  # difference between the two teams
    std_dev_diff = (standard_point_deviation ** 2 + standard_point_deviation ** 2) ** 0.5
    z_score = (0 - difference) / std_dev_diff
    probability_away_team_wins = stats.norm.cdf(z_score)
    probability_home_team_wins = 1 - probability_away_team_wins
    # We need to figure when this "day" is starting and ending
    firstGame = min(homeFirstGame, homelastGame, awayFirstGame, awayLastGame)
    lastGame = max(homeFirstGame, homelastGame, awayFirstGame, awayLastGame)
    time_remaining = calculateTimeRemaining(firstGame, lastGame)
    time_adjustment = 1 + (1 - time_remaining) ** 2 * 0.5  # Exponential decay so the effects are muted until the end
    if home_team > away_team:
        probability_home_team_wins *= time_adjustment
        probability_away_team_wins = 1 - probability_home_team_wins
        return probability_home_team_wins, probability_away_team_wins
    else:
        probability_away_team_wins *= time_adjustment
        probability_home_team_wins = 1 - probability_away_team_wins
        return probability_away_team_wins, probability_home_team_wins


def playerAVGPoints(player: Player, team_name: str) -> float:
    # Find the fantasy team by its name
    leagueTeam = None
    for teamSearch in league.teams:
        if teamSearch.team_name == team_name:
            leagueTeam = teamSearch
            break

    if leagueTeam is None:
        return 0.0

    # Find the matching player on that team
    for playerCheck in leagueTeam.roster:
        if player.name == playerCheck.name:
            stats = playerCheck.stats or {}

            # Prefer the stats for the current league year, e.g. '2026_total'
            year_key = f"{league.year}_total"
            total_stats = stats.get(year_key)

            # If that key isn't there, fall back to any *_total key
            if total_stats is None:
                for k, v in stats.items():
                    if k.endswith("_total"):
                        total_stats = v
                        break

            if not total_stats:
                return 0.0

            avg = total_stats.get("applied_avg")

            try:
                return float(avg)
            except (TypeError, ValueError):
                return 0.0

    # Player not found on that team: treat as 0
    return 0.0

from datetime import datetime

def get_latest_game_points(player: Player):
    """
    Return (points, date) for the most recent individual scoring period
    for this player, using player.stats.

    points: float
    date:   datetime or None
    """
    stats = player.stats or {}

    latest_period = None
    latest_entry = None

    for key, entry in stats.items():
        key_str = str(key)

        # Skip season totals, projections, rolling windows
        if key_str.endswith("_total") or "projected" in key_str or "last_" in key_str:
            continue
        if not isinstance(entry, dict):
            continue

        # Try to treat key as scoring period id (e.g. '35')
        try:
            period_num = int(key_str)
        except ValueError:
            continue

        if latest_period is None or period_num > latest_period:
            latest_period = period_num
            latest_entry = entry

    if latest_entry is None:
        return 0.0, None

    applied = latest_entry.get("applied_total")
    game_date = latest_entry.get("date")  # may be datetime or None

    try:
        pts = float(applied)
    except (TypeError, ValueError):
        pts = 0.0

    return pts, game_date


def get_current_game_clock(proTeam: str, response: dict):
    for game in response['response']:
        #print(game)
        homeName = game["teams"]["home"]["name"]
        awayName = game["teams"]["visitors"]["name"]
        if (proTeam == homeName or proTeam == awayName):
            clock = game["status"]["clock"]
            if clock is not None:
                if clock[1] == ':':
                    clock = int(clock[0])
                else:
                    clock = int(clock[:2])
            return getCurrentGameMinute(game["periods"]["current"], game["status"]["clock"])

    return 0, 0


def teamProjectScore(team: list, team_name: str, response: dict, gameDay: date):
    team_projected_points = 0.0

    # These are basically ignored in calculateTimeRemaining anyway,
    # but we keep them so the function signature still works.
    firstGame = 16
    lastGame = 21

    for player in team:
        # Skip bench / IR / injured
        if player.lineupSlot in ("BE", "IR") or player.injured:
            continue

        # Use our local schedule JSON instead of player.schedule
        if not is_team_playing_on(player.proTeam, gameDay):
            continue

        # Current fantasy points already scored today
        applied_total = float(player.points or 0.0)

        # Season average from the league stats (we made this always numeric earlier)
        player_avg = float(playerAVGPoints(player, team_name) or 0.0)

        # Get where we are in the current game
        currentPeriod, currentClock = get_current_game_clock(player.proTeam, response)
        currentMinute = getCurrentGameMinute(currentPeriod, currentClock)

        # Use the same basic logic you had before, but a bit more defensive
        if currentMinute <= 0:
            # Game hasn't started / we can't find it → use average
            team_projected_points += player_avg
        elif currentMinute >= 48:
            # Game is over → use what they actually scored
            team_projected_points += applied_total
        else:
            # In-progress game: project remaining points from their PPM
            if currentMinute == 0:  # extra safety, though we already guarded above
                team_projected_points += player_avg
            else:
                playerPPM = applied_total / currentMinute
                projected_points_rest = playerPPM * (48 - currentMinute)
                team_projected_points += projected_points_rest

    return round(team_projected_points), firstGame, lastGame


def scoreboard(week: int = None) -> List[Matchup]:
    return league.scoreboard(week)


def getCurrentGameMinute(period: int, clock: int):
    minutes = (period * 12) - clock  # I feel like this will need to be refined eventually so that's why it's a function
    return minutes


def get_team_data(team_id: int) -> Team:
    return league.teams[team_id]


def is_game_today(schedule: dict) -> bool:
    today = datetime.now().date()
    for game in schedule.values():
        if game['date'].date() == today:
            return True
    return False

# I'm not pleased with these two functions being separate but finding the best way to combine them isn't my top
# priority right now
def get_game_start_time(schedule: dict) -> int:
    today = datetime.now().date()
    for game in schedule.values():
        if game['date'].date() == today:
            return game['date'].time().hour
    return 0


def calculateTimeRemaining(firstGame: int, lastGame: int):
    firstGame = 16
    lastGame = 21
    currentTime = datetime.now().hour
    if (currentTime < firstGame):
        return 1
    if (currentTime > lastGame):
        return 0
    return 1 - (currentTime - firstGame) / (lastGame - firstGame)
def is_game_on_date(schedule: dict, gameDay: date) -> bool:
    for game in schedule.values():
        if game['date'].date() == gameDay:
            return True
    return False
    # for game in schedule.values():
    #     if game['date'].date() == gameDay:
    #         return True
    # return False

def print_matchup_player_stats(team1_name: str, team2_name: str):
    """
    Debug helper: for a single matchup, print each active player's
    average points vs their points tonight.
    """
    box_scores = league.box_scores(matchup_total=False)

    selected_box = None
    for box in box_scores:
        home_name = box.home_team.team_name
        away_name = box.away_team.team_name
        names = {home_name, away_name}

        if team1_name in names and team2_name in names:
            selected_box = box
            break

    if selected_box is None:
        print(f"Matchup {team1_name} vs {team2_name} not found in current box_scores.")
        return

    from datetime import datetime, timedelta

    def print_team_stats(lineup, fantasy_team_name: str, label: str):
        # Pick whatever slate you’re interested in
        debug_day = datetime.now().date() - timedelta(days=1)
        today = debug_day

        print(f"\n===== {label}: {fantasy_team_name} =====")
        print(f"{'Player':25} {'Avg':>6} {'Tonight':>8} {'% Diff':>8}")
        print("-" * 60)

        for player in lineup:
            if player.lineupSlot in ("BE", "IR"):
                continue
            if not is_team_playing_on(player.proTeam, today):
                continue

            avg = float(playerAVGPoints(player, fantasy_team_name) or 0.0)
            tonight_points = get_latest_game_points(player)

            if avg > 0:
                pct_change = ((tonight_points - avg) / avg) * 100
            else:
                pct_change = 0.0

            print(f"{player.name:25} {avg:6.1f} {tonight_points:8.1f} {pct_change:8.1f}%")

    # Figure out who is home/away in this boxscore
    if selected_box.home_team.team_name == team1_name:
        team1_lineup = selected_box.home_lineup
        team2_lineup = selected_box.away_lineup
    else:
        team1_lineup = selected_box.away_lineup
        team2_lineup = selected_box.home_lineup

    print_team_stats(team1_lineup, team1_name, "Team 1")
    print_team_stats(team2_lineup, team2_name, "Team 2")
    print()  # trailing newline

from pprint import pprint

def debug_player_raw(player: Player):
    """
    Print all raw data on a Player object with no transformation:
    - Basic attributes
    - stats dict (as-is)
    - schedule dict (as-is)
    - full __dict__ (optional, but very useful)
    """
    print("=" * 80)
    print(f"RAW PLAYER DEBUG: {player.name}")
    print("=" * 80)

    # Basic top-level attributes (these are just direct attribute reads)
    print("\n[Basic attributes]")
    basic_attrs = [
        "name",
        "fullName",
        "playerId",
        "proTeam",
        "position",
        "lineupSlot",
        "injured",
        "injuryStatus",
        "ownership",
        "points",
    ]
    for attr in basic_attrs:
        print(f"  {attr}: {getattr(player, attr, None)}")

    # Stats as-is
    print("\n[stats] (raw)")
    pprint(player.stats, indent=2, width=120)

    # Schedule as-is
    print("\n[schedule] (raw)")
    pprint(getattr(player, "schedule", None), indent=2, width=120)

    # Full __dict__ for the truly curious
    print("\n[__dict__] (raw)")
    pprint(player.__dict__, indent=2, width=120)

    print("\n" + "=" * 80 + "\n")

def debug_player_raw_by_name(fantasy_team_name: str, player_name: str):
    """
    Find a player on a fantasy team by name and dump their raw data.
    No transformation of stats/schedule; uses debug_player_raw.
    """
    target_team = None
    for t in league.teams:
        if t.team_name == fantasy_team_name:
            target_team = t
            break

    if target_team is None:
        print(f"Team '{fantasy_team_name}' not found in league.")
        print("Available teams:")
        for t in league.teams:
            print(" ", t.team_name)
        return

    target_player = None
    for p in target_team.roster:
        if p.name == player_name:
            target_player = p
            break

    if target_player is None:
        print(f"Player '{player_name}' not found on team '{fantasy_team_name}'.")
        print("Available players on that team:")
        for p in target_team.roster:
            print(" ", p.name)
        return

    debug_player_raw(target_player)



box_scores = league.box_scores()
box_scores2 = league.box_scores(matchup_period=3)


if __name__ == "__main__":
    debug_player_raw_by_name("Sarr Fox 64", "Anthony Davis")
