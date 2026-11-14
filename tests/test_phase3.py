import json

import numpy as np
import pandas as pd
import pytest

import ml.explain as ex
import ml.forecast as fc
import ml.train_and_tune as tt
import ml.uncertainty as un

needs_models = pytest.mark.skipif(
    not (tt.META_PATH.exists() and un.META_PATH.exists() and fc.META_PATH.exists()),
    reason="run ml.train_and_tune, ml.uncertainty and ml.forecast first")


@pytest.fixture(scope="module")
def prepared():
    return tt.load_prepared()[0]


# ------------------------------------------------------------------ trend
def test_flat_trend_stops_growing_after_cutoff():
    coef = [0.1, -200.0]
    flat, lin = tt.make_trend(coef, 2022), tt.make_trend(coef)
    assert flat(2022) == pytest.approx(lin(2022))
    assert flat(2025) == pytest.approx(flat(2022))        # no growth after the cutoff
    assert lin(2025) > lin(2022)                           # the linear one keeps rising


# ------------------------------------------------------------------ SHAP
@needs_models
def test_shap_contributions_add_up_to_the_prediction(prepared):
    bundle = tt.load_bundle()
    rows = prepared[prepared.season >= 2023].head(200)
    c = ex.contributions(bundle, rows)
    log_pred = c.sum(axis=1).values + c.attrs["trend"]
    assert np.allclose(np.exp(log_pred), tt.predict_values(bundle, rows), rtol=1e-3)


@needs_models
def test_explanation_waterfall_sums_to_predicted_value(prepared):
    bundle = tt.load_bundle()
    rows = prepared[prepared.season >= 2023].head(25)
    for e in ex.explain_rows(bundle, rows, top_n=4):
        total = e["baseline_value_eur"] + sum(f["effect_eur"] for f in e["factors"])
        assert abs(total - e["predicted_value_eur"]) <= 0.001 * e["predicted_value_eur"] + 30
        assert len(e["factors"]) <= 5                      # 4 concepts + "All other factors"


@needs_models
def test_every_model_feature_maps_to_a_named_concept():
    cols = json.loads(tt.META_PATH.read_text())["columns"]
    unmapped = [c for c in cols if ex.concept_of(c).startswith("Other")]
    assert unmapped == []


# ------------------------------------------------------------- uncertainty
def test_conformal_qhat_reaches_target_coverage_on_calibration_data():
    rng = np.random.default_rng(0)
    y = rng.normal(0, 1, 2000)
    lo, hi = np.full(2000, -0.5), np.full(2000, 0.5)       # deliberately too narrow
    qhat = un.conformal_qhat(lo, hi, y, alpha=0.2)
    assert qhat > 0
    assert ((y >= lo - qhat) & (y <= hi + qhat)).mean() >= 0.8


def test_interval_always_contains_the_point_and_never_crosses():
    class Fixed:
        def __init__(self, v): self.v = np.asarray(v, float)
        def predict(self, X): return self.v
    lo_m, hi_m = Fixed([2.0, 0.0, 1.0]), Fixed([1.0, 1.0, 1.0])   # first row has crossed quantiles
    point = np.array([3.0, 0.5, 1.0])
    lo, hi = un.interval_log(lo_m, hi_m, None, 0.0, point)
    assert (lo <= hi).all() and (lo <= point).all() and (point <= hi).all()


@needs_models
def test_saved_ranges_are_ordered_and_roughly_calibrated(prepared):
    meta = json.loads(un.META_PATH.read_text())
    assert 75 <= meta["metrics"]["test_coverage_pct"] <= 90
    bundle = un.load()
    rows = prepared[prepared.season >= 2023].head(300)
    pt = tt.predict_values(tt.load_bundle(), rows)
    iv = un.predict_interval(bundle, rows, point_eur=pt)
    assert (iv.low_eur <= pt).all() and (pt <= iv.high_eur).all() and (iv.low_eur > 0).all()


# --------------------------------------------------------------- forecasting
def test_next_value_pairs_use_only_the_following_season():
    p = pd.DataFrame({"player_id": [1, 1, 1, 2], "season": [2019, 2020, 2022, 2019],
                      tt.TARGET: [10.0, 20.0, 40.0, 5.0]})
    out = fc.add_next_value(p)
    assert out.next_value.iloc[0] == 20.0                  # 2019 -> 2020
    assert np.isnan(out.next_value.iloc[1])                # no 2021 row, so no 2020 -> 2022 pairing
    assert np.isnan(out.next_value.iloc[3])


@needs_models
def test_forecast_features_do_not_depend_on_the_future_value(prepared):
    _, _, _, builder, trend, meta = fc.load()
    p = fc.add_next_value(prepared)
    rows = p.index[p.season == 2021][:200]
    X1, _ = fc.make_xy(p, rows, builder, trend, meta["groups"])
    q = p.copy()
    q["next_value"] = q["next_value"] * 1000               # wreck the future values
    X2, _ = fc.make_xy(q, rows, builder, trend, meta["groups"])
    pd.testing.assert_frame_equal(X1, X2)


@needs_models
def test_forecast_works_without_any_future_data_and_is_ordered(prepared):
    bundle = fc.load()
    latest = prepared[prepared.season == prepared.season.max()].head(300)   # no next season exists
    out = fc.forecast_next(bundle, latest.drop(columns=["next_value"], errors="ignore"))
    assert (out.low_eur <= out.forecast_eur).all() and (out.forecast_eur <= out.high_eur).all()
    assert (out.forecast_eur > 0).all() and out.forecast_eur.notna().all()


@needs_models
def test_forecast_beats_the_unchanged_baseline_in_saved_metrics():
    m = json.loads(fc.META_PATH.read_text())["metrics"]
    assert m["test_median_APE"] < m["baseline_unchanged_median_APE"]
