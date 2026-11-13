"""Phase 3.2: prediction ranges with a coverage guarantee (conformalized quantile regression).

Instead of one number, give an 80% range ("EUR 20-35M"). Two steps:

 1. Train two XGBoost quantile models (10th and 90th percentile of log value).
    They let the range be wider for uncertain players (few minutes, odd profile)
    and narrower for predictable ones.
 2. Calibrate on held-out seasons (2021-22): measure how often the real value
    fell outside the raw range, and widen the range by exactly the amount that
    makes ~80% of calibration players fall inside (split conformal / CQR).

The quantile models train on seasons before 2021 only, so the calibration seasons
are genuinely unseen. Coverage is then checked on the test seasons (2023+).
Market values drift over time, so test coverage can fall a little under the
target; the report shows the real number, not the target.

    python -m ml.uncertainty
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

import ml.train_and_tune as tt
from ml.feature_engineering import TARGET, FeatureBuilder

ROOT = tt.ROOT
LO_PATH = ROOT / "models" / "scoutlens_q10_v2.json"
HI_PATH = ROOT / "models" / "scoutlens_q90_v2.json"
META_PATH = ROOT / "models" / "scoutlens_quantile_v2_meta.json"
REPORT_PATH = ROOT / "reports" / "phase3_uncertainty.txt"
ALPHA = 0.20          # 80% range = 10th to 90th percentile
CAL_FROM = tt.VAL_FROM  # calibration seasons: 2021-2022


def fit_quantile_models(Xtr, ytr, params: dict, alpha: float = ALPHA):
    """Lower (alpha/2) and upper (1-alpha/2) quantile models on the detrended log target."""
    keep = {k: v for k, v in params.items() if k != "n_estimators"}
    n = min(int(params.get("n_estimators", 400)), 600)
    out = []
    for q in (alpha / 2, 1 - alpha / 2):
        m = XGBRegressor(objective="reg:quantileerror", quantile_alpha=q, n_estimators=n, **keep)
        out.append(m.fit(Xtr, ytr))
    return out


def conformal_qhat(lo, hi, y, alpha: float = ALPHA) -> float:
    """CQR adjustment: the amount (log units) to widen BOTH sides so that
    about (1 - alpha) of calibration points land inside. Can be negative (narrow)."""
    scores = np.maximum(lo - y, y - hi)
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    return float(np.quantile(scores, level, method="higher"))


def interval_log(lo_m, hi_m, X, qhat: float, point_log=None):
    lo = lo_m.predict(X) - qhat
    hi = hi_m.predict(X) + qhat
    lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)           # no crossing quantiles
    if point_log is not None:                                  # the point estimate is always inside
        lo, hi = np.minimum(lo, point_log), np.maximum(hi, point_log)
    return lo, hi


def coverage_table(df: pd.DataFrame, lo, hi, y, predicted) -> pd.DataFrame:
    """Coverage and width overall and by group (so you can see where ranges are weak).
    Value tiers use the PREDICTED value (what a user knows), not the true value: grouping by
    the true value makes cheap players look badly covered, which is a selection artifact."""
    inside = (y >= lo) & (y <= hi)
    width = hi / lo
    rows = {"ALL": (inside.mean() * 100, np.median(width), len(df))}
    groups = {
        "position": df.position,
        "league": df.league,
        "minutes": pd.cut(df.minutes, [-1, 900, 1800, 1e9], labels=["<900", "900-1800", ">1800"]),
        "predicted value": pd.cut(np.asarray(predicted), [0, 2e6, 10e6, 30e6, 1e12], labels=["<2M", "2-10M", "10-30M", ">30M"]),
    }
    for gname, g in groups.items():
        for k in sorted(pd.Series(g).dropna().unique(), key=str):
            m = np.asarray(g == k)
            if m.sum() >= 30:
                rows[f"{gname}: {k}"] = (inside[m].mean() * 100, np.median(width[m]), int(m.sum()))
    return pd.DataFrame(rows, index=["coverage_%", "median_hi/lo", "n"]).T.round(2)


def save(lo_m, hi_m, builder, coef, groups, extra_cols, columns, qhat, metrics, cutoff=None):
    lo_m.save_model(str(LO_PATH))
    hi_m.save_model(str(HI_PATH))
    META_PATH.write_text(json.dumps(dict(
        alpha=ALPHA, qhat=qhat, groups=groups, extra_cols=extra_cols, trend_coef=coef, trend_cutoff=cutoff,
        columns=list(columns), trained_before_season=CAL_FROM, calibrated_on=[CAL_FROM, tt.TEST_FROM - 1],
        metrics=metrics,
        builder=dict(leagues=builder.leagues_, subpos=builder.subpos_, foot=builder.foot_,
                     countries=builder.countries_, height_median=builder.height_median_,
                     top_countries=builder.top_countries)), indent=2))


def load():
    meta = json.loads(META_PATH.read_text())
    lo_m, hi_m = XGBRegressor(), XGBRegressor()
    lo_m.load_model(str(LO_PATH))
    hi_m.load_model(str(HI_PATH))
    b = FeatureBuilder(meta["builder"]["top_countries"])
    b.leagues_, b.subpos_, b.foot_ = (meta["builder"][k] for k in ("leagues", "subpos", "foot"))
    b.countries_, b.height_median_ = meta["builder"]["countries"], meta["builder"]["height_median"]
    return lo_m, hi_m, b, tt.make_trend(meta["trend_coef"], meta.get("trend_cutoff")), meta


def predict_interval(bundle, prepared: pd.DataFrame, point_eur=None) -> pd.DataFrame:
    """80% value range in EUR for rows produced by ml.feature_engineering.prepare()."""
    lo_m, hi_m, builder, trend, meta = bundle
    X = builder.transform(prepared, trend, meta["groups"])
    if meta["extra_cols"] and "external" in meta["groups"]:
        X = X.join(prepared[meta["extra_cols"]])
    X = X[meta["columns"]]
    off = np.asarray(trend(prepared["season"]), float)
    point_log = None if point_eur is None else np.log(np.asarray(point_eur, float)) - off
    lo, hi = interval_log(lo_m, hi_m, X, meta["qhat"], point_log)
    return pd.DataFrame({"low_eur": np.exp(lo + off), "high_eur": np.exp(hi + off)}, index=prepared.index)


def main():
    lines = []

    def log(s=""):
        print(s)
        lines.append(str(s))

    p, extra_cols = tt.load_prepared()
    point_meta = json.loads(tt.META_PATH.read_text())
    groups, params = point_meta["groups"], point_meta["params"]

    fit_idx = p.index[p.season < CAL_FROM]
    cal_idx = p.index[(p.season >= CAL_FROM) & (p.season < tt.TEST_FROM)]
    test_idx = p.index[p.season >= tt.TEST_FROM]
    # same market trend as the saved point model (fitted on seasons < 2023, flat after 2022), so
    # calibration residuals are not polluted by market-level drift
    coef, cutoff = point_meta["trend_coef"], point_meta["trend_cutoff"]
    trend = tt.make_trend(coef, cutoff)
    builder = FeatureBuilder().fit(p.loc[fit_idx])
    Xf, yf = tt.make_xy(p, fit_idx, builder, trend, groups, extra_cols)
    Xc, yc = tt.make_xy(p, cal_idx, builder, trend, groups, extra_cols)
    Xt, yt = tt.make_xy(p, test_idx, builder, trend, groups, extra_cols)

    log(f"quantile models trained on seasons < {CAL_FROM} ({len(fit_idx)} rows); "
        f"calibrated on {CAL_FROM}-{tt.TEST_FROM - 1} ({len(cal_idx)}); tested on {tt.TEST_FROM}+ ({len(test_idx)})\n")
    lo_m, hi_m = fit_quantile_models(Xf, yf, params)

    lo_c, hi_c = lo_m.predict(Xc), hi_m.predict(Xc)
    qhat = conformal_qhat(lo_c, hi_c, yc.values)
    log(f"Calibration: raw range covered {((yc >= lo_c) & (yc <= hi_c)).mean() * 100:.1f}% of 2021-22 players "
        f"(target {100 * (1 - ALPHA):.0f}%); conformal widening = {qhat:+.3f} log units each side")

    off_t = np.asarray(trend(p.loc[test_idx, "season"]), float)
    y_eur = np.exp(yt.values + off_t)
    lo_raw, hi_raw = interval_log(lo_m, hi_m, Xt, 0.0)
    lo_adj, hi_adj = interval_log(lo_m, hi_m, Xt, qhat)

    sub = p.loc[test_idx]
    log("\nTEST seasons 2023+ (never used to fit or calibrate):")
    summary = pd.DataFrame({
        "raw quantile range": [((yt >= lo_raw) & (yt <= hi_raw)).mean() * 100, np.median(np.exp(hi_raw - lo_raw))],
        "calibrated range": [((yt >= lo_adj) & (yt <= hi_adj)).mean() * 100, np.median(np.exp(hi_adj - lo_adj))],
    }, index=["coverage_%", "median_hi/lo"]).T.round(2)
    log(summary.to_string())

    # the saved point model (trained on < 2023) is what the API will show; check the final intervals around it
    bundle_pt = tt.load_bundle()
    pt = tt.predict_values(bundle_pt, sub)
    q_bundle = (lo_m, hi_m, builder, trend, dict(groups=groups, extra_cols=extra_cols, qhat=qhat,
                                                 columns=list(Xf.columns)))
    iv = predict_interval(q_bundle, sub, point_eur=pt)
    inside = ((sub[TARGET] >= iv.low_eur) & (sub[TARGET] <= iv.high_eur))
    log(f"\nFinal intervals around the saved point model: coverage {inside.mean() * 100:.1f}%, "
        f"median width {np.median(iv.high_eur / iv.low_eur):.2f}x (high/low)")

    log("\nCoverage by group (calibrated range, test seasons):")
    tab = coverage_table(sub, np.exp(lo_adj + off_t), np.exp(hi_adj + off_t), y_eur, pt)
    log(tab.to_string())

    log("\nNote: if coverage lands under the 80% target, market values drifted between the calibration\n"
        "seasons (2021-22) and the test seasons (2023+). Re-calibrate on the newest seasons whenever\n"
        "new data is added. Per-league calibration was tried and did not help.")
    metrics = dict(test_coverage_pct=round(float(inside.mean() * 100), 2),
                   test_median_width_ratio=round(float(np.median(iv.high_eur / iv.low_eur)), 3),
                   target_coverage_pct=100 * (1 - ALPHA))
    save(lo_m, hi_m, builder, coef, groups, extra_cols, Xf.columns, qhat, metrics, cutoff)
    q = load()
    again = predict_interval(q, sub, point_eur=pt)
    assert np.allclose(again.values, iv.values, rtol=1e-4), "saved quantile models do not reproduce intervals"
    log("\nSaved models/scoutlens_q10_v2.json, scoutlens_q90_v2.json, scoutlens_quantile_v2_meta.json. Reload check passed.")
    REPORT_PATH.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
