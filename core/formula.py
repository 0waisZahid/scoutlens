"""Interpretable valuation formula (the baseline to beat).

    log(value) = b0
               + age_curve(age)              # quadratic, peaks mid/late 20s
               + position effect
               + league tier effect
               + contract effect             # capped at 4 years
               + performance score           # position-aware z-scored per-90 stats
               + minutes effect

Coefficients are fit by ridge regression on log(value), so you can read off
exactly what the model believes (e.g. "each year of contract left = +X%").
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV

from core.schema import PERFORMANCE, POSITIONS, TARGET

PER90 = [c for c in PERFORMANCE if c.endswith("_p90")]


def position_zscores(df: pd.DataFrame, ref: pd.DataFrame | None = None) -> pd.DataFrame:
    """Z-score each per-90 stat within position (a good striker's xG != a good CB's)."""
    ref = df if ref is None else ref
    out = pd.DataFrame(index=df.index, columns=PER90, dtype=float)
    for pos in POSITIONS:
        r = ref[ref.position == pos]
        m = df.position == pos
        mu, sd = r[PER90].mean(), r[PER90].std().replace(0, 1)
        out.loc[m] = ((df.loc[m, PER90] - mu) / sd).values
    return out.fillna(0)


def build_matrix(df: pd.DataFrame, ref: pd.DataFrame | None = None) -> pd.DataFrame:
    z = position_zscores(df, ref)
    X = pd.DataFrame(index=df.index)
    a = df.age - 26
    X["age"], X["age_sq"] = a, a ** 2
    X["contract"] = df.contract_years_left.clip(upper=4)
    X["tier"] = df.league_tier
    X["minutes_k"] = df.minutes / 1000
    for p in POSITIONS[1:]:
        X[f"pos_{p}"] = (df.position == p).astype(float)
    # compact performance score + individual z-scores
    X["perf_score"] = z.mean(axis=1)
    for c in PER90:
        X[f"z_{c}"] = z[c]
    return X


class FormulaModel:
    def fit(self, df: pd.DataFrame):
        self.ref_ = df.copy()
        X = build_matrix(df)
        self.cols_ = list(X.columns)
        self.mu_, self.sd_ = X.mean(), X.std().replace(0, 1)
        self.model_ = RidgeCV(alphas=np.logspace(-2, 3, 20)).fit(
            (X - self.mu_) / self.sd_, np.log(df[TARGET])
        )
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = build_matrix(df, self.ref_)[self.cols_]
        return np.exp(self.model_.predict((X - self.mu_) / self.sd_))

    def explain(self) -> pd.DataFrame:
        """Coefficients per 1 unit of each raw feature, as % change in value."""
        coef = self.model_.coef_ / self.sd_.values
        return (
            pd.DataFrame({"pct_change_per_unit": (np.exp(coef) - 1) * 100}, index=self.cols_)
            .sort_values("pct_change_per_unit", key=abs, ascending=False)
        )
