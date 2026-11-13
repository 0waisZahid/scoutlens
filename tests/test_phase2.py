import json

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBRegressor

import ml.train_and_tune as tt
from ml.feature_engineering import TARGET, FeatureBuilder, _prev_season_cols, _tenure, prepare
from ml.train_improved import load

ENGINEERED = [
    "club_strength_lag", "club_rel_league", "move_delta", "prev_minutes", "prev_goals_p90",
    "roll_goals_p90", "recent_minutes", "tenure", "club_changed", "new_signing",
    "minutes_share", "ga_share", "goals_z", "assists_z", "prev_value", "prev_value_age_months",
]


@pytest.fixture(scope="module")
def data():
    df = load()
    mv = pd.read_csv(tt.ROOT / "data/processed/market_values.csv")
    return df, mv


def test_tenure_and_prev_season_logic():
    df = pd.DataFrame({
        "player_id": [1, 1, 1, 1, 2, 2],
        "season":    [2019, 2020, 2021, 2022, 2019, 2021],
        "club_id":   [10, 10, 10, 20, 10, 10],
        "minutes":   [900, 1800, 2700, 3000, 500, 600],
        "goals":     [1, 2, 3, 4, 0, 1],
        "assists":   [0, 0, 0, 0, 0, 0],
    })
    assert _tenure(df).tolist() == [0, 1, 2, 0, 0, 0]          # moves and gaps reset tenure
    prev = _prev_season_cols(df)
    assert prev.prev_minutes.tolist()[:4] == [pytest.approx(np.nan, nan_ok=True), 900, 1800, 2700]
    assert np.isnan(prev.prev_minutes.iloc[5])                   # player 2 has no 2020 row
    assert prev.prev_club_id.iloc[3] == 10                       # came from club 10


def test_no_same_or_future_season_value_leakage(data):
    """Changing market values in season S must not change any feature of rows in seasons <= S."""
    df, mv = data
    S = 2020
    base = prepare(df, mv)
    df2 = df.copy()
    df2.loc[df2.season == S, TARGET] *= 1000
    mv2 = mv.copy()
    mv2["date"] = pd.to_datetime(mv2["date"])
    mv2.loc[mv2["date"] >= pd.Timestamp(f"{S}-08-01"), "value_eur"] *= 1000   # all values from season S on
    changed = prepare(df2, mv2)
    rows = df.season <= S
    for c in ENGINEERED:
        a, b = base.loc[rows, c].astype(float), changed.loc[rows, c].astype(float)
        assert np.allclose(a.fillna(-999), b.fillna(-999)), f"feature {c} leaks values from season >= {S}"


def test_feature_columns_consistent_and_no_leaky_club_feature(data):
    df, mv = data
    p = prepare(df, mv)
    tr = p[p.season < 2023]
    coef = tt.fit_trend_coef(tr)
    trend = tt.make_trend(coef)
    fb = FeatureBuilder().fit(tr)
    Xtr = fb.transform(tr, trend)
    Xte = fb.transform(p[p.season >= 2023], trend)
    assert list(Xtr.columns) == list(Xte.columns)
    assert "club_strength" not in Xtr.columns            # the same-season (leaky) version is never used
    assert "club_strength_lag" in Xtr.columns


def test_extra_feature_file_is_merged(tmp_path, monkeypatch):
    df = load()
    ex = pd.DataFrame({"player_id": df.player_id.iloc[:50], "season": df.season.iloc[:50],
                       "contract_years_left": np.arange(50) % 5, "note": ["x"] * 50})
    f = tmp_path / "ext.csv"
    ex.to_csv(f, index=False)
    p, cols = tt.load_prepared(str(f))
    assert cols == ["contract_years_left"]                # text column ignored
    assert len(p) == len(df)
    assert p.contract_years_left.notna().sum() == 50


def test_save_and_load_bundle_roundtrip(data, tmp_path, monkeypatch):
    df, mv = data
    p = prepare(df, mv)
    groups = ["base", "extra", "club", "history"]
    tr, te = tt.split(p, "test")
    tr = tr[::10]                                          # small and fast
    coef = tt.fit_trend_coef(p.loc[tr])
    trend = tt.make_trend(coef)
    fb = FeatureBuilder().fit(p.loc[tr])
    X, y = tt.make_xy(p, tr, fb, trend, groups, [])
    model = XGBRegressor(n_estimators=30, max_depth=3).fit(X, y)
    mp, metap = tmp_path / "m.json", tmp_path / "meta.json"
    monkeypatch.setattr(tt, "MODEL_PATH", mp)
    monkeypatch.setattr(tt, "META_PATH", metap)
    tt.save_bundle(model, fb, coef, groups, [], {"n_estimators": 30}, {}, X.columns)
    bundle = tt.load_bundle(mp, metap)
    rows = p.loc[te[:200]]
    Xte, _ = tt.make_xy(p, rows.index, fb, trend, groups, [])
    expect = np.exp(model.predict(Xte) + trend(rows.season))
    assert np.allclose(tt.predict_values(bundle, rows), expect, rtol=1e-4)


def test_committed_model_metadata_is_leak_free():
    if not tt.META_PATH.exists():
        pytest.skip("model not trained yet")
    meta = json.loads(tt.META_PATH.read_text())
    assert "club_strength" not in meta["columns"]
    assert meta["trained_before_season"] == 2023
