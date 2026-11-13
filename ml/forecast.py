"""Phase 3.3: forecast a player's value one season ahead, with a range.

Inputs known at the end of season t (stats, history, club, and the player's current
value) -> predicted value at the end of season t+1. The model predicts the change
relative to the overall market trend, then converts back to euros. Ranges use the same
conformalized quantile method as ml/uncertainty.py.

Training uses only pairs whose t+1 season is before 2023; the 2023+ seasons are scored
once. It is compared with a no-skill baseline, because beating it is the real test:
  unchanged       next value = current value (with the flat market trend this is also
                  the "market-adjusted" baseline)

    python -m ml.forecast                 # train, evaluate, save
    python -m ml.forecast "Name"          # forecast a player's next season
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRegressor

import ml.train_and_tune as tt
import ml.uncertainty as un
from ml.evaluate import compare
from ml.feature_engineering import TARGET, FeatureBuilder

ROOT = tt.ROOT
PATHS = {k: ROOT / "models" / f"scoutlens_forecast_{k}_v1.json" for k in ("point", "q10", "q90")}
META_PATH = ROOT / "models" / "scoutlens_forecast_v1_meta.json"
REPORT_PATH = ROOT / "reports" / "phase3_forecast.txt"
TEST_NEXT_FROM = tt.TEST_FROM          # test pairs: value season t+1 >= 2023
CAL_T = (2020, 2021)                   # calibration pairs: t in 2020-2021 (t+1 = 2021-22)
FIT_T_BEFORE = 2020                    # quantile models: t < 2020


def add_next_value(p: pd.DataFrame) -> pd.DataFrame:
    nxt = p[["player_id", "season", TARGET]].copy()
    nxt["season"] -= 1
    nxt = nxt.rename(columns={TARGET: "next_value"})
    m = p[["player_id", "season"]].merge(nxt, on=["player_id", "season"], how="left")
    out = p.copy()
    out["next_value"] = m["next_value"].values
    return out


def make_xy(p, rows, builder, trend, groups):
    X = builder.transform(p.loc[rows], trend, groups)
    cur = np.log(p.loc[rows, TARGET]) - trend(p.loc[rows, "season"])
    X = X.assign(cur_log_value=cur)
    y = None
    if "next_value" in p.columns and p.loc[rows, "next_value"].notna().all():
        y = np.log(p.loc[rows, "next_value"]) - trend(p.loc[rows, "season"] + 1) - cur   # excess change
    return X, y


def to_eur(delta_log, p_rows, trend):
    s = p_rows["season"]
    return np.exp(np.log(p_rows[TARGET]) - trend(s) + delta_log + trend(s + 1))


def forecast_next(bundle, prepared: pd.DataFrame) -> pd.DataFrame:
    """Next-season forecast and 80% range for rows from ml.feature_engineering.prepare()."""
    point, lo_m, hi_m, builder, trend, meta = bundle
    X, _ = make_xy(prepared, prepared.index, builder, trend, meta["groups"])
    X = X[meta["columns"]]
    d = point.predict(X)
    lo, hi = un.interval_log(lo_m, hi_m, X, meta["qhat"], d)
    out = pd.DataFrame({"current_value_eur": prepared[TARGET],
                        "forecast_eur": to_eur(d, prepared, trend),
                        "low_eur": to_eur(lo, prepared, trend),
                        "high_eur": to_eur(hi, prepared, trend)}, index=prepared.index)
    out["expected_change_pct"] = (out.forecast_eur / out.current_value_eur - 1) * 100
    return out


def save(point, lo_m, hi_m, builder, coef, groups, columns, qhat, metrics, cutoff=None):
    for k, m in zip(("point", "q10", "q90"), (point, lo_m, hi_m)):
        m.save_model(str(PATHS[k]))
    META_PATH.write_text(json.dumps(dict(
        groups=groups, trend_coef=coef, trend_cutoff=cutoff, columns=list(columns), qhat=qhat, metrics=metrics,
        builder=dict(leagues=builder.leagues_, subpos=builder.subpos_, foot=builder.foot_,
                     countries=builder.countries_, height_median=builder.height_median_,
                     top_countries=builder.top_countries)), indent=2))


def load(paths=PATHS, meta_path=META_PATH):
    meta = json.loads(meta_path.read_text())
    ms = []
    for k in ("point", "q10", "q90"):
        m = XGBRegressor()
        m.load_model(str(paths[k]))
        ms.append(m)
    b = FeatureBuilder(meta["builder"]["top_countries"])
    b.leagues_, b.subpos_, b.foot_ = (meta["builder"][k] for k in ("leagues", "subpos", "foot"))
    b.countries_, b.height_median_ = meta["builder"]["countries"], meta["builder"]["height_median"]
    return ms[0], ms[1], ms[2], b, tt.make_trend(meta["trend_coef"], meta.get("trend_cutoff")), meta


def train_and_evaluate(log=print):
    p, _ = tt.load_prepared()
    p = add_next_value(p)
    groups = json.loads(tt.META_PATH.read_text())["groups"]
    params = {k: v for k, v in json.loads(tt.META_PATH.read_text())["params"].items() if k != "n_estimators"}

    paired = p.next_value.notna()
    train = p.index[paired & (p.season + 1 < TEST_NEXT_FROM)]
    test = p.index[paired & (p.season + 1 >= TEST_NEXT_FROM)]
    # one market trend for every forecast component: fitted on all seasons < 2023, flat after 2022
    pm = json.loads(tt.META_PATH.read_text())
    coef, cutoff = pm["trend_coef"], pm["trend_cutoff"]
    trend = tt.make_trend(coef, cutoff)
    builder = FeatureBuilder().fit(p.loc[train])
    Xtr, ytr = make_xy(p, train, builder, trend, groups)
    Xte, yte = make_xy(p, test, builder, trend, groups)
    log(f"pairs: train {len(train)} (value season <= {TEST_NEXT_FROM - 1}) | test {len(test)} (value season >= {TEST_NEXT_FROM})\n")

    # choose number of trees on the most recent training pairs, then refit on everything
    is_val = p.loc[train, "season"].isin(CAL_T).values
    es = XGBRegressor(n_estimators=1500, early_stopping_rounds=40, eval_metric="rmse", **params)
    es.fit(Xtr[~is_val], ytr[~is_val], eval_set=[(Xtr[is_val], ytr[is_val])], verbose=False)
    n_trees = int((es.best_iteration + 1) * 1.1)
    point = XGBRegressor(n_estimators=n_trees, **params).fit(Xtr, ytr)
    log(f"trees chosen on validation pairs: {n_trees}")

    sub = p.loc[test]
    pred_eur = to_eur(point.predict(Xte), sub, trend)
    actual = sub["next_value"]
    base_unchanged = sub[TARGET]

    log("\nTEST: forecast of next season's value (value seasons 2023+, scored once)")
    tab = compare({"model": pred_eur, "unchanged (no skill)": base_unchanged}, actual)
    log(tab.to_string())

    act_chg = np.log(actual / sub[TARGET])
    mod_chg = np.log(pred_eur / sub[TARGET])
    rho = spearmanr(mod_chg, act_chg).statistic
    big = np.abs(act_chg) > np.log(1.15)
    dir_model = (np.sign(mod_chg[big]) == np.sign(act_chg[big])).mean() * 100
    log(f"\nRank correlation of predicted vs actual value change: {rho:.2f}  (0 = no skill)")
    log(f"Among players whose value moved >15%: direction (up/down) called right {dir_model:.0f}% of the time "
        f"(50% = coin flip)")

    # ranges: quantile models on t < 2020, calibrated on t in 2020-21, same recipe as ml/uncertainty.py
    fit_q = p.index[paired & (p.season < FIT_T_BEFORE)]
    cal_q = p.index[paired & p.season.isin(CAL_T)]
    builder_q = builder      # one shared builder, so point and range models see identical columns
    Xq, yq = make_xy(p, fit_q, builder_q, trend, groups)
    Xc, yc = make_xy(p, cal_q, builder_q, trend, groups)
    Xt2, yt2 = make_xy(p, test, builder_q, trend, groups)
    lo_m, hi_m = un.fit_quantile_models(Xq, yq, params)
    qhat = un.conformal_qhat(lo_m.predict(Xc), hi_m.predict(Xc), yc.values)
    lo, hi = un.interval_log(lo_m, hi_m, Xt2, qhat)
    inside = ((yt2.values >= lo) & (yt2.values <= hi))
    width = float(np.median(np.exp(hi - lo)))
    log(f"\n80% forecast range on test pairs: coverage {inside.mean() * 100:.1f}% (target 80%), "
        f"median width {width:.2f}x (high/low)")

    metrics = dict(test_median_APE=float(tab.loc["model", "median_APE_%"]),
                   baseline_unchanged_median_APE=float(tab.loc["unchanged (no skill)", "median_APE_%"]),
                   rank_corr=float(rho), range_coverage_pct=float(inside.mean() * 100))
    # the saved forecaster uses the quantile models' own builder/trend for ranges, point model for the centre
    save(point, lo_m, hi_m, builder_q, coef, groups, Xtr.columns, qhat, metrics, cutoff)
    return metrics, p, point, builder, trend


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?")
    args = ap.parse_args()
    if args.name:
        bundle = load()
        p, _ = tt.load_prepared()
        hit = p[p["name"].str.contains(args.name, case=False, na=False)]
        if hit.empty:
            raise SystemExit(f"No player matching {args.name!r}")
        row = hit.sort_values("season").tail(1)
        f = forecast_next(bundle, row).iloc[0]
        print(f"{row.iloc[0]['name']} (season {int(row.iloc[0]['season'])} -> next season)")
        print(f"  current value   EUR {f.current_value_eur:,.0f}")
        print(f"  forecast        EUR {f.forecast_eur:,.0f}  ({f.expected_change_pct:+.0f}%)")
        print(f"  80% range       EUR {f.low_eur:,.0f} - {f.high_eur:,.0f}")
        return
    lines = []

    def log(s=""):
        print(s)
        lines.append(str(s))

    train_and_evaluate(log)
    log(f"\nSaved {', '.join(p.name for p in PATHS.values())} and {META_PATH.name}")
    REPORT_PATH.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
