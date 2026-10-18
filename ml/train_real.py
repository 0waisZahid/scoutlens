"""Real-data pipeline in its own file, so no one else's code is modified.

    python -m ml.train_real
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from xgboost import XGBRegressor

from core.schema import POSITIONS, TARGET
from ml.evaluate import compare

ROOT = Path(__file__).resolve().parent.parent
POS_MAP = {"Goalkeeper": "GK", "Defender": "DF", "Midfield": "MF", "Attack": "FW"}
LEAGUES = ["ES1", "FR1", "IT1", "L1"]   # GB1 is the baseline league
PER90 = ["goals_p90", "assists_p90"]
TEST_FROM = 2023                         # train before this season, test from it onward


def load_real(path: str = "data/processed/player_seasons.csv") -> pd.DataFrame:
    df = pd.read_csv(ROOT / path).rename(columns={
        "value_eur": TARGET, "goals_per90": "goals_p90", "assists_per90": "assists_p90",
    })
    df["position"] = df["position"].map(POS_MAP)
    return df.dropna(subset=["position", TARGET, "age"])


def build_matrix(df: pd.DataFrame, ref: pd.DataFrame | None = None) -> pd.DataFrame:
    ref = df if ref is None else ref
    z = pd.DataFrame(0.0, index=df.index, columns=PER90)
    for pos in POSITIONS:                # z-score stats within each position
        r, m = ref[ref.position == pos], df.position == pos
        if m.sum() and len(r):
            mu, sd = r[PER90].mean(), r[PER90].std().replace(0, 1)
            z.loc[m] = ((df.loc[m, PER90] - mu) / sd).values
    X = pd.DataFrame(index=df.index)
    a = df.age - 26
    X["age"], X["age_sq"] = a, a ** 2
    X["season"] = df.season - 2018       # market values inflate over time
    X["minutes_k"] = df.minutes / 1000
    for lg in LEAGUES:
        X[f"lg_{lg}"] = (df.league == lg).astype(float)
    for p in POSITIONS[1:]:
        X[f"pos_{p}"] = (df.position == p).astype(float)
    X["perf_score"] = z.mean(axis=1)
    for c in PER90:
        X[f"z_{c}"] = z[c]
    return X


class FormulaReal:
    def fit(self, df):
        self.ref_ = df.copy()
        X = build_matrix(df)
        self.cols_ = list(X.columns)
        self.mu_, self.sd_ = X.mean(), X.std().replace(0, 1)
        self.model_ = RidgeCV(alphas=np.logspace(-2, 3, 20)).fit(
            (X - self.mu_) / self.sd_, np.log(df[TARGET]))
        return self

    def predict(self, df):
        X = build_matrix(df, self.ref_)[self.cols_]
        return np.exp(self.model_.predict((X - self.mu_) / self.sd_))

    def explain(self):
        coef = self.model_.coef_ / self.sd_.values
        return (pd.DataFrame({"pct_change_per_unit": (np.exp(coef) - 1) * 100}, index=self.cols_)
                .sort_values("pct_change_per_unit", key=abs, ascending=False))


class XGBReal:
    def fit(self, df):
        self.ref_ = df.copy()
        X = build_matrix(df)
        self.cols_ = list(X.columns)
        self.model_ = XGBRegressor(
            n_estimators=400, learning_rate=0.03, max_depth=4,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        ).fit(X, np.log(df[TARGET]))
        return self

    def predict(self, df):
        return np.exp(self.model_.predict(build_matrix(df, self.ref_)[self.cols_]))


if __name__ == "__main__":
    df = load_real()
    train, test = df[df.season < TEST_FROM], df[df.season >= TEST_FROM]
    print(f"train: {len(train)} rows (seasons {train.season.min()}-{train.season.max()})")
    print(f"test:  {len(test)} rows (seasons {test.season.min()}-{test.season.max()})\n")

    formula, xgb = FormulaReal().fit(train), XGBReal().fit(train)
    preds = {
        "naive_median": np.full(len(test), train[TARGET].median()),
        "formula": formula.predict(test),
        "xgboost": xgb.predict(test),
    }
    preds["blend"] = np.sqrt(preds["formula"] * preds["xgboost"])
    print("Held-out (future seasons) results:")
    print(compare(preds, test[TARGET]))
    print("\nWhat the formula believes (top effects):")
    print(formula.explain().head(12).round(1))
    