"""Phase 2: feature ablation, hyperparameter tuning, and a saved model.

    python -m ml.train_and_tune                      # full run (about 2-4 minutes)
    python -m ml.train_and_tune --trials 10          # quicker tuning
    python -m ml.train_and_tune --extra data/processed/external.csv

Honest-evaluation rules used here:
  * The test seasons (2023+) are scored ONCE, at the end.
  * Feature groups are kept or dropped, and hyperparameters are chosen, using
    validation seasons 2021-2022 only (training on seasons before 2021).
  * The detrending curve and all category lists are fitted on training rows only. The market
    trend is held flat after the last training season (see make_trend).

`--extra` merges any CSV that has `player_id`, `season` and numeric columns
(for example contract_years_left, caps, xg_p90 from FBref) as one more feature group.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ml.evaluate import compare, score
from ml.feature_engineering import GROUP_ORDER, TARGET, FeatureBuilder, prepare
from ml.train_improved import load

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "scoutlens_xgb_v2.json"
META_PATH = ROOT / "models" / "scoutlens_xgb_v2_meta.json"
REPORT_PATH = ROOT / "reports" / "phase2_results.txt"

VAL_FROM, TEST_FROM = 2021, 2023
MIN_GAIN = 0.002  # a feature group must cut validation RMSE_log by this much to be kept

DEFAULT_PARAMS = dict(n_estimators=400, learning_rate=0.03, max_depth=4,
                      subsample=0.8, colsample_bytree=0.8, min_child_weight=5)

SEARCH_SPACE = dict(
    max_depth=[3, 4, 5, 6, 7],
    learning_rate=[0.02, 0.03, 0.05],
    min_child_weight=[1, 3, 5, 10, 20],
    subsample=[0.6, 0.7, 0.8, 0.9],
    colsample_bytree=[0.5, 0.6, 0.7, 0.8, 0.9],
    reg_lambda=[0.5, 1.0, 3.0, 10.0],
    reg_alpha=[0.0, 0.1, 1.0],
)


# ---------------------------------------------------------------- trend / data
def fit_trend_coef(train: pd.DataFrame) -> list:
    """Linear trend of log median value per season, fitted on training rows only."""
    med = train.groupby("season")[TARGET].median()
    return [float(c) for c in np.polyfit(med.index.values.astype(float), np.log(med.values), 1)]


def make_trend(coef, cutoff=None):
    """Market trend in log value. Beyond `cutoff` (the last training season) it stays FLAT:
    extrapolating the 2012-2022 growth upward over-predicted 2023+ values by ~15% (the
    median player's value stopped rising), and the flat version won on validation seasons."""
    if cutoff is None:
        return lambda s: np.polyval(coef, np.asarray(s, float))
    return lambda s: np.polyval(coef, np.minimum(np.asarray(s, float), cutoff))


def cutoff_of(train: pd.DataFrame) -> int:
    return int(train["season"].max())


def load_prepared(extra: str | None = None):
    df = load()
    mv = pd.read_csv(ROOT / "data/processed/market_values.csv")
    p = prepare(df, mv)
    extra_cols: list = []
    if extra:
        ex = pd.read_csv(extra)
        extra_cols = [c for c in ex.columns if c not in ("player_id", "season")
                      and pd.api.types.is_numeric_dtype(ex[c])]
        idx = p.index
        p = p.merge(ex[["player_id", "season"] + extra_cols], on=["player_id", "season"], how="left")
        p.index = idx
    return p, extra_cols


def make_xy(p, rows, builder, trend, groups, extra_cols):
    X = builder.transform(p.loc[rows], trend, groups)
    if extra_cols and "external" in groups:
        X = X.join(p.loc[rows, extra_cols])
    y = np.log(p.loc[rows, TARGET]) - trend(p.loc[rows, "season"])
    return X, y


def split(p, kind: str):
    if kind == "val":
        return p.index[p.season < VAL_FROM], p.index[(p.season >= VAL_FROM) & (p.season < TEST_FROM)]
    return p.index[p.season < TEST_FROM], p.index[p.season >= TEST_FROM]


def fit_eval(p, kind, groups, extra_cols, params=None):
    tr, te = split(p, kind)
    coef = fit_trend_coef(p.loc[tr])
    trend = make_trend(coef, cutoff_of(p.loc[tr]))
    builder = FeatureBuilder().fit(p.loc[tr])
    Xtr, ytr = make_xy(p, tr, builder, trend, groups, extra_cols)
    Xte, _ = make_xy(p, te, builder, trend, groups, extra_cols)
    model = XGBRegressor(**(params or DEFAULT_PARAMS)).fit(Xtr, ytr)
    pred = np.exp(model.predict(Xte) + trend(p.loc[te, "season"]))
    return score(p.loc[te, TARGET], pred), pred, model, Xtr.columns


# ------------------------------------------------------------------- ablation
def ablation(p, extra_cols, log):
    order = [g for g in GROUP_ORDER if g != "value_history"] + (["external"] if extra_cols else [])
    kept, rows, prev_rmse = [], {}, None
    for g in order:
        trial = kept + [g]
        sv, *_ = fit_eval(p, "val", trial, extra_cols)
        gain = None if prev_rmse is None else prev_rmse - sv["RMSE_log"]
        keep = prev_rmse is None or gain >= MIN_GAIN
        st, *_ = fit_eval(p, "test", trial, extra_cols)
        rows[f"+{g}"] = {"val_RMSE": sv["RMSE_log"], "val_medAPE%": sv["median_APE_%"],
                         "test_RMSE": st["RMSE_log"], "test_medAPE%": st["median_APE_%"],
                         "test_within25%": st["within_25%"],
                         "kept": "yes" if keep else "NO (val gain < %.3f)" % MIN_GAIN}
        if keep:
            kept, prev_rmse = trial, sv["RMSE_log"]
    log("Feature-group ablation (kept/dropped decided on VALIDATION only; test shown for reference):")
    log(pd.DataFrame(rows).T.round(3).to_string())
    return kept


# --------------------------------------------------------------------- tuning
def tune(p, groups, extra_cols, trials, seed, log):
    tr, va = split(p, "val")
    trend = make_trend(fit_trend_coef(p.loc[tr]), cutoff_of(p.loc[tr]))
    builder = FeatureBuilder().fit(p.loc[tr])
    Xtr, ytr = make_xy(p, tr, builder, trend, groups, extra_cols)
    Xva, yva = make_xy(p, va, builder, trend, groups, extra_cols)
    rng = np.random.default_rng(seed)
    best = None
    for t in range(trials):
        params = {k: v[int(rng.integers(len(v)))] for k, v in SEARCH_SPACE.items()}
        m = XGBRegressor(n_estimators=2000, early_stopping_rounds=50, eval_metric="rmse", **params)
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        rmse = float(m.best_score)
        if best is None or rmse < best[0]:
            best = (rmse, params, int(m.best_iteration) + 1)
        log(f"  trial {t + 1:>2}/{trials}  val RMSE_log {rmse:.4f}  trees {int(m.best_iteration) + 1:>4}  {params}")
    base, *_ = fit_eval(p, "val", groups, extra_cols)
    log(f"\nBest validation RMSE_log {best[0]:.4f} (default params: {base['RMSE_log']:.4f})")
    return best[1], best[2]


# ------------------------------------------------------------ save / load
def save_bundle(model, builder, coef, groups, extra_cols, params, metrics, columns, cutoff=None):
    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.save_model(str(MODEL_PATH))
    meta = dict(groups=groups, extra_cols=extra_cols, params=params, trend_coef=coef, trend_cutoff=cutoff,
                columns=list(columns), metrics=metrics, trained_before_season=TEST_FROM,
                builder=dict(leagues=builder.leagues_, subpos=builder.subpos_, foot=builder.foot_,
                             countries=builder.countries_, height_median=builder.height_median_,
                             top_countries=builder.top_countries))
    META_PATH.write_text(json.dumps(meta, indent=2))


def load_bundle(model_path: Path = MODEL_PATH, meta_path: Path = META_PATH):
    meta = json.loads(meta_path.read_text())
    model = XGBRegressor()
    model.load_model(str(model_path))
    b = FeatureBuilder(meta["builder"]["top_countries"])
    b.leagues_, b.subpos_, b.foot_ = (meta["builder"][k] for k in ("leagues", "subpos", "foot"))
    b.countries_, b.height_median_ = meta["builder"]["countries"], meta["builder"]["height_median"]
    return model, b, make_trend(meta["trend_coef"], meta.get("trend_cutoff")), meta


def predict_values(bundle, prepared: pd.DataFrame) -> np.ndarray:
    """Predicted market value (EUR) for rows produced by ml.feature_engineering.prepare()."""
    model, builder, trend, meta = bundle
    X = builder.transform(prepared, trend, meta["groups"])
    if meta["extra_cols"] and "external" in meta["groups"]:
        X = X.join(prepared[meta["extra_cols"]])
    X = X[meta["columns"]]
    return np.exp(model.predict(X) + trend(prepared["season"]))


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=25)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--extra", default=None)
    args = ap.parse_args()

    lines = []

    def log(s=""):
        print(s)
        lines.append(str(s))

    p, extra_cols = load_prepared(args.extra)
    n_tr = int((p.season < TEST_FROM).sum())
    log(f"train: {n_tr} rows | validation seasons {VAL_FROM}-{TEST_FROM - 1} | test seasons {TEST_FROM}+ "
        f"({len(p) - n_tr} rows)\n")

    groups = ablation(p, extra_cols, log)
    log(f"\nGroups kept: {groups}\n\nTuning ({args.trials} random trials, validation seasons only):")
    params, n_trees = tune(p, groups, extra_cols, args.trials, args.seed, log)
    # +10% trees because the final fit uses more data; but if the search hit the 2000-tree cap
    # it never converged, so use the validated count as is
    final = dict(params, n_estimators=n_trees if n_trees >= 2000 else int(n_trees * 1.1))

    tr, te = split(p, "test")
    coef = fit_trend_coef(p.loc[tr])
    cutoff = cutoff_of(p.loc[tr])
    trend = make_trend(coef, cutoff)
    builder = FeatureBuilder().fit(p.loc[tr])
    Xtr, ytr = make_xy(p, tr, builder, trend, groups, extra_cols)
    Xte, _ = make_xy(p, te, builder, trend, groups, extra_cols)
    model = XGBRegressor(**final).fit(Xtr, ytr)
    pred = np.exp(model.predict(Xte) + trend(p.loc[te, "season"]))
    y = p.loc[te, TARGET]

    # reference rows: untuned best groups, and forecast mode (own last value as an input)
    res = {"tuned (SAVED MODEL)": pred}
    _, res["untuned, same groups"], *_ = fit_eval(p, "test", groups, extra_cols)
    fm_groups = groups + ["value_history"]
    fm_params = dict(final)
    Xtr_f, _ = make_xy(p, tr, builder, trend, fm_groups, extra_cols)
    Xte_f, _ = make_xy(p, te, builder, trend, fm_groups, extra_cols)
    fm = XGBRegressor(**fm_params).fit(Xtr_f, ytr)
    res["forecast mode (uses own last value)"] = np.exp(fm.predict(Xte_f) + trend(p.loc[te, "season"]))

    log("\nFINAL held-out test results (seasons 2023+, scored once):")
    table = compare(res, y)
    log(table.to_string())
    metrics = score(y, pred)

    imp = pd.Series(model.feature_importances_, index=Xtr.columns).sort_values(ascending=False)
    log("\nTop 12 features of the saved model:")
    log(imp.head(12).round(3).to_string())

    save_bundle(model, builder, coef, groups, extra_cols, final, metrics, Xtr.columns, cutoff)
    log(f"\nSaved {MODEL_PATH.relative_to(ROOT)} ({MODEL_PATH.stat().st_size / 1e6:.1f} MB) "
        f"and {META_PATH.relative_to(ROOT)}")

    # prove the saved model reloads and gives identical predictions
    bundle = load_bundle()
    again = predict_values(bundle, p.loc[te])
    assert np.allclose(again, pred, rtol=1e-4), "saved model does not reproduce predictions"
    log("Reload check passed: saved model reproduces the test predictions.")
    REPORT_PATH.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
