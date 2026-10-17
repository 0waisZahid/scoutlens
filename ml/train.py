"""Train + compare the formula baseline against XGBoost.

    python -m ml.train                     # simulated data
    python -m ml.train path/to/real.csv    # real data (must match core/schema.py)
"""
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

from core.formula import FormulaModel, build_matrix
from core.schema import TARGET
from etl.load import load_players
from ml.evaluate import compare


class XGBModel:
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


def cross_validate(df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    preds = {"formula": np.zeros(len(df)), "xgboost": np.zeros(len(df))}
    for tr, te in KFold(k, shuffle=True, random_state=0).split(df):
        a, b = df.iloc[tr], df.iloc[te]
        preds["formula"][te] = FormulaModel().fit(a).predict(b)
        preds["xgboost"][te] = XGBModel().fit(a).predict(b)
    preds["blend"] = np.sqrt(preds["formula"] * preds["xgboost"])
    return compare(preds, df[TARGET])


if __name__ == "__main__":
    df = load_players(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"{len(df)} players\n")
    print("5-fold out-of-sample results:")
    print(cross_validate(df))
    print("\nWhat the formula believes (top effects):")
    print(FormulaModel().fit(df).explain().head(12).round(1))
