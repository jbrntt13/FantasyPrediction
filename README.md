# FantasyPrediction

Backend for live win-probability predictions in an ESPN fantasy basketball
points league. It samples each player's per-game fantasy history (built from
`nba_api` box scores and the league's scoring rules) to Monte Carlo simulate
today's matchups and the full fantasy week, and adjusts in real time while NBA
games are in progress.

The frontend lives in
[FantasyPredictionVisuals](https://github.com/jbrntt13/FantasyPredictionVisuals).

## Layout

| Path | Purpose |
| --- | --- |
| `api_server.py` | FastAPI app: `/odds/today`, `/odds/weekly`, `/odds/custom`, `/health`, demo controls |
| `config.py` | All season/credential/path settings, read from env or `.env` |
| `fantasy.py` | ESPN league connection (`league`) used by everything else |
| `simulate_matchup.py` | Daily Monte Carlo, with live in-game adjustment |
| `weekly_sim.py` | Full-week Monte Carlo |
| `live_odds.py` | NBA live scoreboard, game-fraction and partial-game projection |
| `nbaTest.py` | Local NBA schedule lookup (who plays on a given day) |
| `NBAintegration.py` | nba_api game logs plus the league scoring formula |
| `fetch_fantasy_players_history.py` | Builds `data/fantasy_player_history_<season>.json` from scratch |
| `patch_missing_players.py` | Adds new roster players and new games to the history file |
| `demo_mode.py` | Replays a cached week with a fake clock, no network needed |
| `data/` | Per-season inputs: NBA schedule and player history |
| `cache/` | Dated `*_projScore.json` and `*_weekly_odds.json` outputs |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then fill in ESPN_S2 / ESPN_SWID
```

### Getting your ESPN cookies

The league is private, so ESPN needs two cookies to let the API read it.
They expire periodically, so expect to refresh them about once a season.

1. Log in at <https://fantasy.espn.com> in Chrome or Firefox and open your league.
2. Open DevTools (F12 or right-click, Inspect).
3. Chrome: **Application** tab, left sidebar **Storage > Cookies > https://fantasy.espn.com**.
   Firefox: **Storage** tab, **Cookies > https://fantasy.espn.com**.
4. Copy the **Value** of `espn_s2` into `ESPN_S2`. It is a long string and
   may contain `%2B`, `%2F`, `%3D`. Paste it exactly as shown.
5. Copy the **Value** of `SWID` into `ESPN_SWID`, including the curly braces,
   for example `{F3126586-12DD-4281-9D5B-515865B5FC66}`.

Never commit `.env`. It is git-ignored.

### New season checklist

1. Set `ESPN_YEAR` in `.env` to the year the season **ends** (2026-27 is `2027`).
   Leaving it blank auto-detects from today's date.
2. Download the NBA schedule and save it as
   `data/scheduleLeagueV2_<season>.json`, for example:
   ```bash
   curl -o data/scheduleLeagueV2_2026-27.json \
     https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json
   ```
3. Build the player history file (this is slow on purpose, it sleeps between
   players to respect nba_api rate limits):
   ```bash
   python fetch_fantasy_players_history.py
   ```
   Early in the season every player has only a handful of games, so
   predictions will be noisy for the first few weeks.
4. Run `python patch_missing_players.py` periodically (or hit
   `GET /patch_missing_players`) to pick up new games and roster changes.

## Running

```bash
uvicorn api_server:app --reload --port 8000
```

Docker:

```bash
docker build -t fantasy-prediction .
docker run --env-file .env -p 8000:8000 fantasy-prediction
```

### Demo mode

Replays a cached week without touching ESPN or the NBA. Needs
`cache/<monday>_weekly_odds.json` for the chosen week, which exist for most of
Dec 2025 through early Feb 2026.

```bash
DEMO_DATE=2026-02-06 DEMO_SPEED=60 uvicorn api_server:app --port 8000
```

Then `POST /demo/reset`, `/demo/skip?hours=N`, `/demo/set-speed?speed=N`,
`/demo/set-fraction?fraction=0.5`, and `GET /demo/status`.

## Known limitations

- Weekly odds use calendar Monday to Sunday, not ESPN matchup periods, so
  the first and last weeks of the season and any multi-week periods are off.
- League scoring values are hardcoded in both `live_odds.py` and
  `NBAintegration.py`. Update both if the league settings change.
- `custom_matchup.py` is an incomplete duplicate of `simulate_matchup.py`
  and is not used by the API.
