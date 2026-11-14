"""Phase 3.1: explain why the model valued a player the way it did.

Uses XGBoost's built-in TreeSHAP (`pred_contribs`). This is the same algorithm as
the `shap` library's TreeExplainer (verified to give identical numbers), without
the version-compatibility problems between shap and xgboost.

How to read the numbers
-----------------------
The model works in log space:  log(value) = baseline + sum(contributions) + market trend.
So every contribution is a MULTIPLIER on value: a contribution of +0.20 means
"this factor raised the value by about 22%" (exp(0.20) - 1). Contributions are
grouped into human concepts (Age, League, Club strength, ...). The euro waterfall
adds the concepts one at a time, largest effect first, so it sums exactly to the
prediction; the percent effects do not depend on that order.

    python -m ml.explain "Name"         # explain a player's latest season
    python -m ml.explain --global       # which concepts matter most overall
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
import xgboost as xgb

import ml.train_and_tune as tt

CONCEPTS = [  # (concept, matcher): first match wins
    ("Age", lambda f: f in ("age", "age_sq")),
    ("League", lambda f: f.startswith("lg_")),
    ("Position", lambda f: f.startswith(("pos_", "sub_"))),
    ("Playing time", lambda f: f in ("minutes_k", "appearances", "prev_minutes_k", "recent_minutes_k")),
    ("Goals & assists (this season)", lambda f: f in ("goals_p90", "assists_p90")),
    ("Recent form (last 2 seasons)", lambda f: f in ("prev_goals_p90", "prev_assists_p90",
                                                      "roll_goals_p90", "roll_assists_p90")),
    ("Club strength", lambda f: f in ("club_strength_lag", "club_rel_league")),
    ("Club tenure & moves", lambda f: f in ("tenure", "club_changed", "new_signing", "move_delta")),
    ("Discipline", lambda f: f in ("yellow_p90", "red_p90")),
    ("Physical", lambda f: f == "height" or f.startswith("foot_")),
    ("Nationality", lambda f: f.startswith("nat_")),
    ("Share of club output", lambda f: f in ("minutes_share", "ga_share", "goals_z", "assists_z")),
    ("Own previous value", lambda f: f in ("prev_log_value", "prev_value_age_months")),
]


def concept_of(feature: str) -> str:
    for name, match in CONCEPTS:
        if match(feature):
            return name
    return f"Other ({feature})"


def contributions(bundle, prepared: pd.DataFrame) -> pd.DataFrame:
    """Per-feature SHAP contributions in log space, one row per player (plus a `bias` column)."""
    model, builder, trend, meta = bundle
    X = builder.transform(prepared, trend, meta["groups"])
    if meta["extra_cols"] and "external" in meta["groups"]:
        X = X.join(prepared[meta["extra_cols"]])
    X = X[meta["columns"]]
    raw = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    out = pd.DataFrame(raw.astype("float64"), index=prepared.index, columns=list(X.columns) + ["bias"])
    out.attrs["X"] = X
    out.attrs["trend"] = np.asarray(trend(prepared["season"]), float)
    return out


def explain_rows(bundle, prepared: pd.DataFrame, top_n: int = 6) -> list:
    """One explanation dict per row. Safe to call from an API."""
    contrib = contributions(bundle, prepared)
    X, trend = contrib.attrs["X"], contrib.attrs["trend"]
    feats = [c for c in contrib.columns if c != "bias"]
    concept_of_feat = {f: concept_of(f) for f in feats}
    results = []
    for k, idx in enumerate(contrib.index):
        row = contrib.loc[idx]
        by_concept = row[feats].groupby(concept_of_feat).sum()
        base_log = float(row["bias"]) + float(trend[k])
        total_log = base_log + float(by_concept.sum())
        order = by_concept.reindex(by_concept.abs().sort_values(ascending=False).index)

        steps, running = [], base_log
        shown = order.iloc[:top_n]
        rest = order.iloc[top_n:].sum()
        for name, c in list(shown.items()) + ([("All other factors", rest)] if len(order) > top_n else []):
            before = np.exp(running)
            running += float(c)
            steps.append({"concept": name, "effect_pct": round((np.exp(float(c)) - 1) * 100, 1),
                          "effect_eur": round(float(np.exp(running) - before)),
                          "log_effect": round(float(c), 4)})
        age = float(X.loc[idx, "age"]) + 26 if "age" in X.columns else None
        results.append({
            "index": idx,
            "predicted_value_eur": round(float(np.exp(total_log))),
            "baseline_value_eur": round(float(np.exp(base_log))),   # average player of that season
            "age": age,
            "factors": steps,
        })
    return results


def format_explanation(e: dict, name: str = "") -> str:
    lines = [f"{name or 'Player'}: predicted value EUR {e['predicted_value_eur']:,}",
             f"Starting point (average player, that season): EUR {e['baseline_value_eur']:,}", ""]
    for f in e["factors"]:
        lines.append(f"  {f['concept']:<34} {f['effect_pct']:>+8.1f}%   (EUR {f['effect_eur']:+,})")
    return "\n".join(lines)


def global_importance(bundle, prepared: pd.DataFrame) -> pd.DataFrame:
    """Mean absolute effect of each concept across many players (as a % change in value)."""
    contrib = contributions(bundle, prepared)
    feats = [c for c in contrib.columns if c != "bias"]
    by = contrib[feats].T.groupby({f: concept_of(f) for f in feats}).sum().T
    imp = (np.exp(by.abs()) - 1).mean() * 100
    return imp.sort_values(ascending=False).round(1).to_frame("avg_effect_%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?")
    ap.add_argument("--global", dest="glob", action="store_true")
    args = ap.parse_args()
    bundle = tt.load_bundle()
    p, _ = tt.load_prepared()
    if args.glob or not args.name:
        print("Average effect of each concept on a player's value (seasons 2023+):")
        print(global_importance(bundle, p[p.season >= tt.TEST_FROM]).to_string())
        return
    hit = p[p["name"].str.contains(args.name, case=False, na=False)]
    if hit.empty:
        raise SystemExit(f"No player matching {args.name!r}")
    row = hit.sort_values("season").tail(1)
    e = explain_rows(bundle, row)[0]
    print(format_explanation(e, f"{row.iloc[0]['name']} ({int(row.iloc[0]['season'])})"))
    print(f"\nTransfermarkt value that season: EUR {int(row.iloc[0][tt.TARGET]):,}")


if __name__ == "__main__":
    main()
