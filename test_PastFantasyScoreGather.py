# test_lauri.py

from NBAintegration import find_nba_player_id, build_fantasy_history_for_player

def test_player(name: str, season: str = "2024-25"):
    nba_id = find_nba_player_id(name)
    if nba_id is None:
        print(f"Could not find NBA ID for '{name}'")
        return

    print(f"Found NBA ID for {name}: {nba_id}")

    history = build_fantasy_history_for_player(nba_id, season=season)

    if not history:
        print("No game history found.")
        return

    print(f"\nTotal games found: {len(history)}\n")

    # Print first 10 games
    print(f"{'Date':<12} {'FPts':>7} {'Opponent':<20}")
    print("-" * 40)
    for h in history[:20]:
        print(f"{h['date']} {h['fantasy_points']:7.2f} {h['opponent']:<20}")

    # Basic stats over the whole history
    fps = [h["fantasy_points"] for h in history]
    avg_f = sum(fps) / len(fps)
    print("\nSummary:")
    print(f"  Min fantasy points: {min(fps):.2f}")
    print(f"  Max fantasy points: {max(fps):.2f}")
    print(f"  Avg fantasy points: {avg_f:.2f}")


if __name__ == "__main__":
    test_player("Lauri Markkanen", season="2025-26")

