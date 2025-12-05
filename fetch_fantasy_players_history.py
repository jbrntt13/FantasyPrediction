# fetch_fantasy_players_history.py

import json
from pathlib import Path
from datetime import datetime, timedelta, date
from fantasy import league  # assumes fantasy.py defines `league = League(...)`
from NBAintegration import (
    find_nba_player_id,
    build_fantasy_history_for_player,
    current_nba_season_str,
)


def fetch_all_fantasy_players_history(output_path: str):
    season = current_nba_season_str()
    print(f"Using NBA season: {season}")

    players_data = {}
    errors = []

    # Walk all fantasy teams & their rosters
    for team in league.teams:
        print(f"Processing team: {team.team_name}")
        for p in team.roster:
            espn_id = getattr(p, "playerId", None)
            name = getattr(p, "name", None)

            if espn_id is None or name is None:
                continue

            # Skip if we've already processed this player
            if espn_id in players_data:
                continue

            print(f"  - {name} (ESPN ID: {espn_id})")

            # Map to NBA ID
            nba_id = find_nba_player_id(name)
            if nba_id is None:
                msg = f"    !! Could not find NBA ID for '{name}' (ESPN ID {espn_id})"
                print(msg)
                errors.append(msg)
                continue

            print(f"    NBA ID: {nba_id}")

            # Fetch fantasy history for this NBA player
            try:
                history_rows = build_fantasy_history_for_player(nba_id, season=season)
            except Exception as e:
                msg = f"    !! Error fetching history for {name} (NBA ID {nba_id}): {e}"
                print(msg)
                errors.append(msg)
                continue

            # Convert date objects to ISO strings for JSON
            history_serializable = []
            for h in history_rows:
                date_val = h["date"]
                if hasattr(date_val, "isoformat"):
                    date_str = date_val.isoformat()
                else:
                    date_str = str(date_val)

                history_serializable.append(
                    {
                        "date": date_str,
                        "fantasy_points": float(h["fantasy_points"]),
                        "opponent": h["opponent"],
                        "game_id": h["game_id"],
                    }
                )

            players_data[espn_id] = {
                "espn_player_id": espn_id,
                "nba_player_id": nba_id,
                "name": name,
                "proTeam": getattr(p, "proTeam", None),
                "season": season,
                "history": history_serializable,
            }
            # 🌟 RATE LIMIT HERE 🌟
            import time
            time.sleep(10)  # or 5–10 seconds if you want to be extremely safe

    # Write everything to a single JSON file
    out_path = Path(output_path)
    out_path.write_text(json.dumps(players_data, indent=2), encoding="utf-8")
    print(f"\nSaved history for {len(players_data)} players → {out_path}")

    if errors:
        print("\nSome issues occurred:")
        for e in errors:
            print("  ", e)


if __name__ == "__main__":
    fetch_all_fantasy_players_history("fantasy_player_history_2025-26.json")
