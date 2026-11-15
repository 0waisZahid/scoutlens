import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app, get_store
from api.store import DataStore, load_store

SEASON_COLUMNS = ["player_id", "name", "position", "league", "season", "age",
                  "minutes", "goals", "assists", "appearances"]


def make_store() -> DataStore:
    seasons = pd.DataFrame([
        (1, "Martin Odegaard", "Midfield", "GB1", 2024, 25.0, 2800, 8, 10, 35),
        (2, "Marcus Rashford", "Attack", "GB1", 2024, 26.0, 2000, 7, 5, 30),
        (3, "Marco Reus", "Attack", "L1", 2023, 34.0, 1500, 4, 6, 28),
        (4, "Mario Nobody", "Defender", "IT1", 2022, 30.0, 900, 0, 1, 12),    # no value history
        (5, "Vinícius Júnior", "Attack", "ES1", 2023, 23.0, 2700, 23, 11, 38),
        (5, "Vinícius Júnior", "Attack", "ES1", 2024, 24.0, 2900, 15, 10, 36),
    ], columns=SEASON_COLUMNS)
    values = pd.DataFrame({
        "player_id": [1, 1, 2, 3, 5, 5],
        "date": ["2023-06-01", "2024-06-01", "2024-06-01", "2023-06-01", "2023-06-01", "2024-06-01"],
        "value_eur": [80e6, 90e6, 60e6, 8e6, 120e6, 150e6],
    })
    return DataStore(seasons, values)


@pytest.fixture
def client():
    store = make_store()
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def names(response):
    return [p["name"] for p in response.json()]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "players": 5}


def test_search_by_first_name_and_by_surname(client):
    assert names(client.get("/players/search", params={"q": "marc"})) == ["Marcus Rashford", "Marco Reus"]
    assert names(client.get("/players/search", params={"q": "rash"})) == ["Marcus Rashford"]


def test_results_ranked_by_latest_value_and_missing_value_last(client):
    r = client.get("/players/search", params={"q": "mar"})
    assert names(r) == ["Martin Odegaard", "Marcus Rashford", "Marco Reus", "Mario Nobody"]


def test_limit_caps_results(client):
    r = client.get("/players/search", params={"q": "mar", "limit": 2})
    assert names(r) == ["Martin Odegaard", "Marcus Rashford"]


def test_accent_and_case_insensitive(client):
    assert names(client.get("/players/search", params={"q": "vinicius"})) == ["Vinícius Júnior"]
    assert names(client.get("/players/search", params={"q": "JUNIOR"})) == ["Vinícius Júnior"]


def test_result_fields(client):
    p = client.get("/players/search", params={"q": "odegaard"}).json()[0]
    assert p == {"player_id": 1, "name": "Martin Odegaard", "position": "Midfield", "league": "GB1",
                 "latest_season": 2024, "age": 25.0, "latest_value_eur": 90_000_000.0}


def test_latest_value_uses_newest_date_and_newest_season(client):
    p = client.get("/players/search", params={"q": "vinicius"}).json()[0]
    assert p["latest_value_eur"] == 150_000_000.0
    assert p["latest_season"] == 2024 and p["age"] == 24.0


def test_player_without_values_has_null_value(client):
    p = client.get("/players/search", params={"q": "mario"}).json()[0]
    assert p["latest_value_eur"] is None


def test_no_match_returns_empty_list(client):
    r = client.get("/players/search", params={"q": "zzzz"})
    assert r.status_code == 200 and r.json() == []


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "mar", "limit": 0}, {"q": "mar", "limit": 51}])
def test_invalid_requests_are_rejected(client, params):
    assert client.get("/players/search", params=params).status_code == 422


def test_real_data_smoke():
    store = load_store()
    assert len(store.players) > 5000
    top = store.search("haal", 1)[0]
    assert top["name"] == "Erling Haaland" and top["position"] == "Attack"
