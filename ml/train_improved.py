"""Improved real-data models: inflation adjustment, extra features, optional club strength.

    python -m ml.train_improved
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ml.evaluate import compare

ROOT = Path(__file__).resolve().parent.parent
TARGET = "market_value_eur"
POS_MAP = {"Goalkeeper": "GK", "Defender": "DF", "Midfield": "MF", "Attack": "FW"}
TEST_FROM = 2023


def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data/processed/player_seasons_club.csv")
    df = df.rename(columns={"value_eur": TARGET})
    df["position"] = df["position"].map(POS_MAP)
    df = df.dropna(subset=["position", TARGET, "age"]).reset_index(drop=True)
    df["height_in_cm"] = df["height_in_cm"].fillna(df["height_in_cm"].median())
    df["sub_position"] = df["sub_position"].fillna("unknown")
    df["foot"] = df["foot"].fillna("unknown")
    # club strength = mean log value of the club's OTHER players that season
    lv = np.log(df[TARGET])
    g = df.assign(lv=lv).groupby(["club_id", "season"])["lv"]
    s, n = g.transform("sum"), g.transform("count")
    df["club_strength"] = np.where(n >= 6, (s - lv) / (n - 1), np.nan)
    return df


def features(df: pd.DataFrame, level: int) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    a = df.age - 26
    X["age"], X["age_sq"] = a, a ** 2
    X["minutes_k"] = df.minutes / 1000
    X["goals_p90"], X["assists_p90"] = df.goals_per90, df.assists_per90
    X = X.join(pd.get_dummies(df.position, prefix="pos").astype(float))
    X = X.join(pd.get_dummies(df.league, prefix="lg").astype(float))
    if level >= 1:
        X["appearances"] = df.appearances
        X["yellow_p90"], X["red_p90"] = df.yellow_cards_per90, df.red_cards_per90
        X["height"] = df.height_in_cm
        X = X.join(pd.get_dummies(df.sub_position, prefix="sub").astype(float))
        X = X.join(pd.get_dummies(df.foot, prefix="foot").astype(float))
    if level >= 2:
        X["club_strength"] = df.club_strength
    return X


def fit_trend(train: pd.DataFrame):
    """Linear trend of log median value per season, fitted on TRAINING years only."""
    med = train.groupby("season")[TARGET].median()
    coef = np.polyfit(med.index.values.astype(float), np.log(med.values), 1)
    return lambda s: np.polyval(coef, np.asarray(s, float))


def run(df, train, test, level, detrend, trend):
    X = features(df, level)
    if level >= 2 and detrend:
        X["club_strength"] = X["club_strength"] - trend(df.season)
    off_tr = trend(train.season) if detrend else 0.0
    off_te = trend(test.season) if detrend else 0.0
    model = XGBRegressor(
        n_estimators=400, learning_rate=0.03, max_depth=4,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
    ).fit(X.loc[train.index], np.log(train[TARGET]) - off_tr)
    return np.exp(model.predict(X.loc[test.index]) + off_te), model, X.columns


if __name__ == "__main__":
    df = load()
    train, test = df[df.season < TEST_FROM], df[df.season >= TEST_FROM]
    trend = fit_trend(train)
    print(f"train: {len(train)} rows | test: {len(test)} rows (seasons {TEST_FROM}+)\n")

    preds = {}
    p, _, _ = run(df, train, test, 0, False, trend); preds["xgb_basic"] = p
    p, _, _ = run(df, train, test, 0, True, trend);  preds["+inflation_adj"] = p
    p, _, _ = run(df, train, test, 1, True, trend);  preds["+extra_features"] = p
    p, m, cols = run(df, train, test, 2, True, trend); preds["+club_strength"] = p

    print("Held-out (future seasons) results:")
    print(compare(preds, test[TARGET]))

    imp = pd.Series(m.feature_importances_, index=cols).sort_values(ascending=False)
    print("\nTop features (last model):")
    print(imp.head(10).round(3))

