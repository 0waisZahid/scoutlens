"""Phase 1.2: how much of the club_strength gain survives without leakage?

Compares four versions of the club_strength feature, all scored on the same
future seasons (2023+), reusing the team's own code from ml/train_improved.py:

  no_club        : no club feature at all (the honest baseline)
  current        : mean log value of the club's OTHER players in the SAME season
                   (this uses other players' target values from the period being
                   predicted, so it is the version that may be inflated)
  lagged_1yr     : mean log value of the club's players in the PREVIOUS season,
                   excluding the player himself (only past information)
  frozen_cutoff  : club strength frozen at the last training season (2022) for
                   every test row (strictest: nothing from the test period)

    python -m ml.leakage_check
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.evaluate import compare
from ml.train_improved import TARGET, TEST_FROM, fit_trend, load, run

MIN_PLAYERS = 6


def club_mean(df: pd.DataFrame, club_season: pd.DataFrame, key_season: pd.Series,
              exclude_self: bool) -> np.ndarray:
    """Mean log value of the club's players in `key_season`, optionally excluding the player."""
    lv = np.log(df[TARGET])
    tmp = df.assign(lv=lv)
    agg = tmp.groupby(["club_id", "season"])["lv"].agg(["sum", "count"]).reset_index()
    look = pd.DataFrame({"club_id": df.club_id.values, "season": key_season.values,
                         "pid": df.player_id.values, "row": np.arange(len(df))})
    look = look.merge(agg, on=["club_id", "season"], how="left")
    s, n = look["sum"].values.astype(float), look["count"].values.astype(float)
    if exclude_self:
        # remove the player's own value from that club-season, if he was in it
        own = tmp[["player_id", "club_id", "season", "lv"]].rename(
            columns={"player_id": "pid", "lv": "own_lv"})
        look = look.merge(own, on=["pid", "club_id", "season"], how="left")
        had = look["own_lv"].notna().values
        s = np.where(had, s - look["own_lv"].fillna(0).values, s)
        n = np.where(had, n - 1, n)
    return np.where(n >= MIN_PLAYERS - 1, s / np.maximum(n, 1), np.nan)


def main() -> None:
    df = load()
    train, test = df[df.season < TEST_FROM], df[df.season >= TEST_FROM]
    trend = fit_trend(train)
    cutoff = TEST_FROM - 1
    print(f"train: {len(train)} rows | test: {len(test)} rows (seasons {TEST_FROM}+)")

    preds = {}
    p, _, _ = run(df, train, test, 1, True, trend)
    preds["no_club"] = p

    d = df.copy()  # current (the team's version, already in df.club_strength)
    p, _, _ = run(d, train, test, 2, True, trend)
    preds["current"] = p

    d = df.copy()
    d["club_strength"] = club_mean(d, None, d.season - 1, exclude_self=True)
    p, _, _ = run(d, train, test, 2, True, trend)
    preds["lagged_1yr"] = p

    d = df.copy()
    frozen_season = pd.Series(np.where(d.season >= TEST_FROM, cutoff, d.season - 1), index=d.index)
    d["club_strength"] = club_mean(d, None, frozen_season, exclude_self=True)
    p, _, _ = run(d, train, test, 2, True, trend)
    preds["frozen_cutoff"] = p

    print("\nHeld-out (future seasons) results:")
    print(compare(preds, test[TARGET]))

    cur, lag, base = (compare({k: preds[k]}, test[TARGET]).iloc[0] for k in ("current", "lagged_1yr", "no_club"))
    print(f"\nMedian error: no_club {base['median_APE_%']:.1f}% -> current {cur['median_APE_%']:.1f}% "
          f"-> lagged {lag['median_APE_%']:.1f}%")
    print("Rows with no usable club_strength (model treats as missing):")
    for name, col in (("lagged_1yr", d.assign(c=club_mean(df, None, df.season - 1, True)).c),):
        print(f"  {name}: {col[test.index].isna().mean() * 100:.1f}% of test rows")


if __name__ == "__main__":
    main()
