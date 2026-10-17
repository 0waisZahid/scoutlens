"""How close are we? Metrics that make sense for market values."""
import numpy as np
import pandas as pd


def score(y_true, y_pred) -> dict:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    ape = np.abs(y_pred - y_true) / y_true
    lt, lp = np.log(y_true), np.log(y_pred)
    ss_res, ss_tot = ((lt - lp) ** 2).sum(), ((lt - lt.mean()) ** 2).sum()
    return {
        "R2_log": 1 - ss_res / ss_tot,
        "RMSE_log": float(np.sqrt(((lt - lp) ** 2).mean())),
        "median_APE_%": float(np.median(ape) * 100),
        "within_25%": float((ape <= 0.25).mean() * 100),
        "within_50%": float((ape <= 0.50).mean() * 100),
    }


def compare(results: dict, y_true) -> pd.DataFrame:
    return pd.DataFrame({k: score(y_true, v) for k, v in results.items()}).T.round(3)
