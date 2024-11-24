import requests, json

team_name_mapping = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls',
    'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',
    'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic',
    'PHL': 'Philadelphia 76ers', 'PHO': 'Phoenix Suns', 'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings',
    'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
}






def fetch_nba_live_games():
    url = "https://api-nba-v1.p.rapidapi.com/games"

    querystring = {"live": "all"}

    headers = {
        "x-rapidapi-key": "d4bfbc4596msh7f5df671e47c27dp1af307jsn849a11cfef2a",
        "x-rapidapi-host": "api-nba-v1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()



    return response.json()

def fetch_nba_schedule():
    url = 'https://api.sportradar.com/nba/trial/v8/en/games/2024/11/20/schedule.json?api_key=UxOA58FMGJNxBTLjvJLDxLzRcgQzGkyqnbxqziYN'
    headers = {'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    print("THIS IS THE HJSON", response.json())
    return response.json()




def fetch_nba_playByplay(game_id):
    print(game_id)
    url = f'https://api.sportradar.com/nba/trial/v8/en/games/{game_id[0]}/pbp.json?api_key=UxOA58FMGJNxBTLjvJLDxLzRcgQzGkyqnbxqziYN'
    headers = {'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    return response.json()


def search_game_id(team_names):
    print(team_names)
    game_ids = []
    for game in schedule.get('games', []):
        print(schedule.get('games', []))
        home_team = game.get('home', {}).get('name')
        away_team = game.get('away', {}).get('name')
        if home_team in team_names or away_team in team_names:
            game_ids.append(game.get('id'))
    return game_ids


# def get_current_period_and_clock(team_name):
#     #team_name = team_name_mapping.get(team_name, 'Unknown Team')
#     #game_ID = search_game_id(team_name)
#     play_by_play_data = fetch_nba_live_games()
#     period = play_by_play_data.get('quarter')
#     clock = play_by_play_data.get('clock')
#     if clock is not None:
#         if clock[1] == ':':
#             clock = int(clock[0])
#         else:
#             clock = int(clock[:2])
#         return period, clock
#     return 0, 0  # default value


# Example usage
fetch_nba_live_games()
team_names = ["Los Angeles Lakers", "Houston Rockets"]
#print(game_ids)
#print(fetch_nba_playByplay('ad3128ea-6925-407c-a5a0-f04c12e25521'))
