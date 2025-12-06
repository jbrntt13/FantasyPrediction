from fantasy import league

def main():
    # ... everything you already have ...

    settings = getattr(league, "settings", None)
    if not settings:
        print("\nNo settings object found on league.")
        return

    print("\n=== RAW matchup_periods ===")
    mps = getattr(settings, "matchup_periods", None)
    print("Type:", type(mps))
    print("Value:", mps)

    if isinstance(mps, list) and mps:
        print("\n=== First matchup_period object attrs ===")
        first = mps[0]
        print("type:", type(first))
        print("dir:", [a for a in dir(first) if not a.startswith("_")])
        try:
            print("dict-ish:", vars(first))
        except TypeError:
            pass

        # Also dump the one for the CURRENT matchup period, if we can find it
        cur_mp = getattr(league, "currentMatchupPeriod", None) or getattr(league, "current_matchup_period", None)
        print("\nCurrent matchup period:", cur_mp)

        for mp in mps:
            # Try a few likely attribute names
            mp_id = getattr(mp, "matchup_period", None)
            if mp_id is None:
                mp_id = getattr(mp, "matchupPeriodId", None)
            if mp_id is None:
                mp_id = getattr(mp, "matchup_period_id", None)

            if mp_id == cur_mp:
                print("\n=== MATCHUP PERIOD OBJECT FOR CURRENT WEEK ===")
                print("attrs:", [a for a in dir(mp) if not a.startswith("_")])
                try:
                    print("dict-ish:", vars(mp))
                except TypeError:
                    pass
                break


if __name__ == "__main__":
    main()
