# patch_missing_players.py
import unicodedata

import json
from pathlib import Path
import time

from fantasy import league
from NBAintegration import (
    find_nba_player_id,
    build_fantasy_history_for_player,
    current_nba_season_str,
)


HISTORY_PATH = Path("fantasy_player_history_2025-26.json")
RATE_LIMIT_SECONDS = 5


def load_history():
    if not HISTORY_PATH.exists():
        raise FileNotFoundError(f"History file not found: {HISTORY_PATH}")
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))


def save_history(history_map):
    HISTORY_PATH.write_text(json.dumps(history_map, indent=2), encoding="utf-8")
    print(f"Saved updated history to {HISTORY_PATH}")


def serialize_history_rows(rows):
    """Convert rows from build_fantasy_history_for_player into JSON-friendly dicts."""
    hist_serializable = []
    for h in rows:
        date_val = h["date"]
        date_str = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
        hist_serializable.append(
            {
                "date": date_str,
                "fantasy_points": float(h["fantasy_points"]),
                "opponent": h["opponent"],
                "game_id": h["game_id"],
            }
        )
    return hist_serializable


def append_new_games(history, pid_str, nba_id, player_name, season):
    """
    Fetch the full season log and append only games we don't already have
    (matching on game_id if present, otherwise on date string).
    """
    try:
        fresh_rows = build_fantasy_history_for_player(nba_id, season=season)
    except Exception as e:
        print(f"!! Error fetching history for {player_name}: {e}")
        return 0
    # Rate limit between player fetches
    time.sleep(RATE_LIMIT_SECONDS)

    existing = history.get(pid_str, {})
    existing_hist = existing.get("history", [])
    existing_game_ids = {h.get("game_id") for h in existing_hist if h.get("game_id")}
    existing_dates = {h.get("date") for h in existing_hist}

    to_add = []
    for row in fresh_rows:
        date_val = row["date"]
        date_str = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
        game_id = row.get("game_id")

        if game_id and game_id in existing_game_ids:
            continue
        if not game_id and date_str in existing_dates:
            continue

        to_add.append(
            {
                "date": date_str,
                "fantasy_points": float(row["fantasy_points"]),
                "opponent": row["opponent"],
                "game_id": game_id,
            }
        )

    if not to_add:
        return 0

    existing_hist.extend(to_add)
    # keep history sorted by date just in case
    existing_hist.sort(key=lambda h: h.get("date", ""))

    history[pid_str] = {
        **existing,
        "nba_player_id": nba_id,
        "history": existing_hist,
        "season": season,
        "name": existing.get("name", player_name),
    }

    return len(to_add)


def main():
    season = current_nba_season_str()
    print(f"Using season: {season}")

    history = load_history()

    # Track missing players
    missing = []

    for team in league.teams:
        print(f"Checking team: {team.team_name}")
        for p in team.roster:
            pid_str = str(p.playerId)
            if pid_str not in history:
                missing.append(p)

    if not missing:
        print("No missing players in history file.")
        return

    print("\nMissing players found:")
    for p in missing:
        print(f"  - {p.name} (ESPN ID {p.playerId}, team {p.proTeam})")

    # If you only want to patch the four you mentioned,
    # you can filter here:
    target_names = {
        "Collin Gillespie",
        "Ryan Nembhard",
        "Santi Aldama",
    }

    to_patch = [p for p in missing if p.name in target_names] or missing

    print("\nPatching these players:")
    for p in to_patch:
        print(f"  - {p.name} (ESPN ID {p.playerId})")

    for p in to_patch:
        nba_id = find_nba_player_id(p.name)
        if nba_id is None:
            print(f"!! Could not find NBA ID for {p.name}, skipping")
            continue

        print(f"Fetching history for {p.name} (NBA ID {nba_id})...")
        try:
            rows = build_fantasy_history_for_player(nba_id, season=season)
        except Exception as e:
            print(f"!! Error fetching history for {p.name}: {e}")
            continue
        # Rate limit between player fetches
        time.sleep(RATE_LIMIT_SECONDS)

        hist_serializable = serialize_history_rows(rows)
        history[str(p.playerId)] = {
            "espn_player_id": p.playerId,
            "nba_player_id": nba_id,
            "name": p.name,
            "proTeam": p.proTeam,
            "season": season,
            "history": hist_serializable,
        }

        print(f"  -> Added {len(hist_serializable)} games for {p.name}")

    # Pass 2: update existing roster players with any games not yet recorded
    print("\nUpdating existing players with new games...")
    updated_count = 0

    for team in league.teams:
        for p in team.roster:
            pid_str = str(p.playerId)
            if pid_str not in history:
                continue  # handled above

            nba_id = history[pid_str].get("nba_player_id") or find_nba_player_id(p.name)
            if nba_id is None:
                print(f"!! Could not find NBA ID for {p.name}, skipping update")
                continue

            added = append_new_games(history, pid_str, nba_id, p.name, season)
            if added:
                print(f"  -> Added {added} new games for {p.name}")
                updated_count += added

    if not updated_count:
        print("No new games to add for existing players.")

    save_history(history)


if __name__ == "__main__":
    main()
