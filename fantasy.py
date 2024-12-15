# NBA Import
from datetime import datetime, timedelta, date
import scipy.stats as stats

import sys
from typing import List

from nbaTest import fetch_nba_live_games

# Add the directory containing the espn_api module to the Python path
sys.path.append('A:\espn-api\espn-api')

from espn_api.basketball import League, Matchup, Player, Team

league = League(league_id=538595081, year=2025,
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


@app.route("/dailyblindprojections")
def dailyblindprojections():
    box = league.box_scores(matchup_total=False)
    projections = []

    for boxscore in box_scores:
        home_team_name = boxscore.home_team.team_name
        away_team_name = boxscore.away_team.team_name

        home_team_projected_points = projectedPoints(boxscore.home_team, boxscore.away_team)[0]
        away_team_projected_points = projectedPoints(boxscore.home_team, boxscore.away_team)[1]
        print(home_team_name, home_team_projected_points, away_team_name, away_team_projected_points)
        chanceHome, chanceAway = simplePrediction(home_team_projected_points, away_team_projected_points)

        projections.append((home_team_name, home_team_projected_points, chanceHome, away_team_name,
                            away_team_projected_points, chanceAway))
    print(projections)
    return projections


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

        home_team_projected_points, homeFirstGame, homeLastGame = teamProjectScore(boxscore.home_lineup, boxscore.home_team.team_name, nbaDATA,
                                                      datetime.now().date())
        away_team_projected_points, homeFirstGame, awayLastGame = teamProjectScore(boxscore.away_lineup, boxscore.away_team.team_name, nbaDATA,
                                                      datetime.now().date())

        chanceHome, chanceAway = simplePrediction(home_team_projected_points, away_team_projected_points)
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


def projectedPoints(home_team: Team, away_team: Team):
    home_team_projected_points = 0
    away_team_projected_points = 0
    for players in home_team.roster:
        if players.lineupSlot != 'BE' and players.lineupSlot != 'IR' and players.injured != True:
            if (is_game_today(players.schedule)):
                home_team_projected_points += playerAVGPoints(players, home_team.team_name)
    for players in away_team.roster:
        if players.lineupSlot != 'BE' and players.lineupSlot != 'IR' and players.injured != True:
            if (is_game_today(players.schedule)):
                away_team_projected_points += playerAVGPoints(players, away_team.team_name)

    return round(home_team_projected_points), round(away_team_projected_points)


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


def playerAVGPoints(player: Player, team_name: str):
    leagueTeam = None
    for teamSearch in league.teams:
        if teamSearch.team_name == team_name:  # this is so stupid I hate it
            leagueTeam = teamSearch
    for playerCheck in leagueTeam.roster:
        if player.name == playerCheck.name:
            return playerCheck.stats.get('2025_total', {}).get('applied_avg', 'Key not found')

    return 0  # Player isn't on the team? Well they may as well be averaging 0

    # boxCheck = league.box_scores(matchup_period=3, matchup_total=False)
    # for box in boxCheck:
    #     if team.team_name in [box.home_team.team_name, box.away_team.team_name]:
    #         relevant_lineup = box.home_lineup if team.team_name == box.home_team.team_name else box.away_lineup
    #         for lineup_player in relevant_lineup:
    #             if lineup_player.name == player.name:
    #                 print(lineup_player.stats)
    #                 return lineup_player.stats.get('2025_total', {}).get('applied_avg', 'Key not found')


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
    team_projected_points = 0
    lastGame = 0
    firstGame = 0
    box_scores = league.box_scores(matchup_total=False)
    for player in team:
        if player.lineupSlot != 'BE' and player.lineupSlot != 'IR' and player.injured != True:
            if is_game_today(player.schedule):
                gameStart = get_game_start_time(player.schedule)
                if(gameStart > lastGame):
                    lastGame = get_game_start_time(player.schedule)
                if(gameStart < firstGame):
                    firstGame = get_game_start_time(player.schedule)
                #get players current points
                applied_total = player.points

                #get players projected points
                player_avg = playerAVGPoints(player, team_name)
                #get how many minutes have passed so far
                currentPeriod, currentClock = get_current_game_clock(player.proTeam, response)
                currentMinute = getCurrentGameMinute(currentPeriod, currentClock)
                #attempt to guess what the player will score at the end of the day
                #(get ppm and multiply by minutes left in the game)
                if currentMinute == 0:
                    team_projected_points += player_avg
                    #  Player hasn't started yet so just return the average
                elif currentMinute > 48:
                    team_projected_points += applied_total
                    # Game is over so just return the applied total
                else:
                    playerPPM = applied_total / currentMinute
                    projected_points = playerPPM * (48 - currentMinute)
                    team_projected_points += projected_points
                    #add that to the total
    return round(team_projected_points), gameStart


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


box_scores = league.box_scores()
box_scores2 = league.box_scores(matchup_period=3)
# print(box_scores2[0].home_lineup[9].name)
# print("box score 2",get_current_period_and_clock(box_scores2[0].home_lineup[0].proTeam))
#teamSnapshotChance(box_scores[0].home_lineup, box_scores[0].home_team.team_name)
# results = box_scores
# matchups = scoreboard(3)
# print(box_scores[0].team)

# for player in box_scores[0].home_lineup:
#     if (player.name == "Jalen Green"):
#         period, clock = get_current_period_and_clock(player.proTeam)
#         print(getCurrentGameMinute(period, clock))
currentOdds()

# for boxscore in box_scores:
#     print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
#     print(boxscore)
#     print(boxscore.home_team, boxscore.away_team)
#     print(boxscore.home_score, boxscore.away_score)

    # projectedscore = projectedPoints(boxscore.home_team, boxscore.away_team)
    # print("Today's projected points: ", projectedscore)
    # daychanceHome, daychanceAway = simplePrediction(projectedscore[0], projectedscore[1])
    # print("Today's chance: ", daychanceHome, daychanceAway)
    #
    # HomeScore = teamProjectScore(boxscore.home_lineup, boxscore.home_team.team_name)
    # AwayScore = teamProjectScore(boxscore.away_lineup, boxscore.away_team.team_name)
    # print("Today's updated points: ", HomeScore, AwayScore)
    # updatedchanceHome, updatedchanceAway = simplePrediction(HomeScore, AwayScore)
    # print("Today's updated chance: ", updatedchanceHome, updatedchanceAway)
