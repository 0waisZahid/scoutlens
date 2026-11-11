import numpy as np
import pandas as pd

from ml.leakage_check import club_mean

TARGET = "market_value_eur"


def make_df():
    rows = []
    pid = 0
    for season in (2021, 2022, 2023):
        for i in range(8):                       # 8 players in club 1 every season
            rows.append((pid := pid + 1, 1, season, 1_000_000 * (i + 1)))
    df = pd.DataFrame(rows, columns=["player_id", "club_id", "season", TARGET])
    df["player_id"] = np.tile(np.arange(8), 3)   # same 8 players each season
    return df


def test_lagged_excludes_player_himself():
    df = make_df()
    cs = club_mean(df, None, df.season - 1, exclude_self=True)
    row = df[(df.season == 2022) & (df.player_id == 0)].index[0]
    others = np.log(df[(df.season == 2021) & (df.player_id != 0)][TARGET]).mean()
    assert np.isclose(cs[row], others)


def test_lagged_ignores_same_and_future_seasons():
    df = make_df()
    before = club_mean(df, None, df.season - 1, exclude_self=True)
    df2 = df.copy()
    df2.loc[df2.season == 2023, TARGET] *= 1000      # wreck the "test" season values
    after = club_mean(df2, None, df2.season - 1, exclude_self=True)
    rows_2023 = df.season == 2023
    assert np.allclose(before[rows_2023], after[rows_2023])   # 2023 features unchanged
