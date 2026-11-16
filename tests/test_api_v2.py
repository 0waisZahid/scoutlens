"""Tests for the analytics endpoints. These use the real saved models and data (about 3 s to load)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app, get_store


@pytest.fixture(scope="module")
def client():
    app.dependency_overrides.clear()
    get_store.cache_clear()
    return TestClient(app)


@pytest.fixture(scope="module")
def haaland(client):
    return client.get("/players/search", params={"q": "haaland"}).json()[0]["player_id"]


def test_meta(client):
    m = client.get("/meta").json()
    assert m["max_season"] >= 2025 and "GB1" in m["leagues"]
    assert {r["id"] for r in m["rankings"]} >= {"value", "undervalued", "risers"}


def test_profile(client, haaland):
    r = client.get(f"/players/{haaland}")
    assert r.status_code == 200
    p = r.json()
    assert p["name"] == "Erling Haaland"
    assert p["seasons"][-1]["club_name"]
    assert p["seasons"] == sorted(p["seasons"], key=lambda s: s["season"])
    assert p["value_history"] and set(p["percentiles"]) == set(p["radar_labels"])
    assert all(v is None or 0 <= v <= 100 for v in p["percentiles"].values())


def test_unknown_player_is_404(client):
    for url in ("/players/999999999", "/players/999999999/valuation", "/players/999999999/similar"):
        assert client.get(url).status_code == 404


def test_valuation_range_and_factors_are_consistent(client, haaland):
    v = client.get(f"/players/{haaland}/valuation").json()
    assert v["low_eur"] <= v["model_value_eur"] <= v["high_eur"]
    # the euro waterfall must rebuild the prediction: baseline x every factor's multiplier
    rebuilt = v["baseline_value_eur"]
    for f in v["factors"]:
        rebuilt *= 1 + f["effect_pct"] / 100
    assert rebuilt == pytest.approx(v["model_value_eur"], rel=0.02)
    assert v["forecast"]["low_eur"] <= v["forecast"]["forecast_eur"] <= v["forecast"]["high_eur"]
    assert v["forecast"]["for_season"] == v["season"] + 1
    assert v["in_sample"] is False and any("compressed" in w for w in v["warnings"])


def test_valuation_for_a_past_season_flags_in_sample_and_gives_the_actual(client, haaland):
    v = client.get(f"/players/{haaland}/valuation", params={"season": 2021}).json()
    assert v["season"] == 2021 and v["in_sample"] is True
    assert v["forecast"]["actual_value_eur"] is not None
    assert client.get(f"/players/{haaland}/valuation", params={"season": 1999}).status_code == 404


def test_rankings_sorted_and_filtered(client):
    r = client.get("/rankings", params={"sort": "value", "position": "GK", "limit": 5}).json()
    vals = [x["market_value_eur"] for x in r["rows"]]
    assert len(vals) == 5 and vals == sorted(vals, reverse=True)
    assert {x["position_code"] for x in r["rows"]} == {"GK"}
    assert [x["rank"] for x in r["rows"]] == [1, 2, 3, 4, 5]


def test_gap_rankings_stay_inside_the_reliable_value_band(client):
    r = client.get("/rankings", params={"sort": "undervalued", "limit": 20}).json()
    assert r["min_value_eur"] == 2e6 and r["max_value_eur"] == 100e6
    gaps = [x["gap_pct"] for x in r["rows"]]
    assert gaps == sorted(gaps, reverse=True) and all(2e6 <= x["market_value_eur"] <= 100e6 for x in r["rows"])
    # and the opposite ranking runs the other way
    o = client.get("/rankings", params={"sort": "overvalued", "limit": 20}).json()["rows"]
    assert [x["gap_pct"] for x in o] == sorted(x["gap_pct"] for x in o)


def test_rankings_bad_input(client):
    assert client.get("/rankings", params={"sort": "nonsense"}).status_code == 422
    assert client.get("/rankings", params={"position": "XX"}).status_code == 422
    assert client.get("/rankings", params={"season": 1900}).status_code == 404


def test_similar_players_exclude_self_and_share_a_role(client, haaland):
    r = client.get(f"/players/{haaland}/similar", params={"k": 5}).json()
    assert r["in_pool"] and len(r["players"]) == 5
    assert haaland not in {p["player_id"] for p in r["players"]}
    dists = [p["distance"] for p in r["players"]]
    assert dists == sorted(dists)
    assert {p["sub_position"] for p in r["players"]} == {"Centre-Forward"}


def test_teammates_and_connections(client, haaland):
    t = client.get(f"/players/{haaland}/teammates", params={"limit": 5}).json()
    assert t["total"] >= len(t["players"]) == 5
    mate = t["players"][0]["player_id"]
    c = client.get("/connections", params={"a": haaland, "b": mate}).json()
    assert c["separation"] == 1
    assert [s["type"] for s in c["path"]] == ["player", "club", "player"]
    back = client.get("/connections", params={"a": mate, "b": haaland}).json()
    assert back["separation"] == 1
    assert client.get("/connections", params={"a": haaland, "b": haaland}).json()["separation"] == 0


def test_model_info(client):
    i = client.get("/model/info").json()
    assert 25 < i["valuation"]["median_APE_%"] < 40
    assert i["global_importance"] and i["data"]["players"] > 5000
