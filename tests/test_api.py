import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.main as api_main
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


def test_query_and_path_parameters_are_bounded(client):
    assert client.get("/players/search", params={"q": "x" * 101}).status_code == 422
    assert client.get("/players/0").status_code == 422
    assert client.get("/players/2147483648").status_code == 422
    assert client.get("/players/1/valuation", params={"season": 1800}).status_code == 422
    assert client.get("/rankings", params={"min_age": "nan"}).status_code == 422
    assert client.get("/rankings", params={"min_value": "inf"}).status_code == 422
    assert client.get("/rankings", params={"min_minutes": 200001}).status_code == 422


def test_inverted_ranking_ranges_are_rejected(client):
    assert client.get("/rankings", params={"min_age": 30, "max_age": 20}).status_code == 422
    assert client.get("/rankings", params={"min_value": 20, "max_value": 10}).status_code == 422


def test_client_errors_do_not_include_internal_lookup_details(client):
    response = client.get("/players/999999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Player not found."}


def test_security_headers_and_development_cors(client):
    response = client.get("/health")
    head = client.head("/health")
    assert head.status_code == 200
    assert head.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "font-src 'self' data:" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"].split("script-src", 1)[1].split(";", 1)[0]
    allowed = client.options("/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    blocked = client.options("/health", headers={
        "Origin": "https://attacker.example",
        "Access-Control-Request-Method": "GET",
    })
    assert "access-control-allow-origin" not in blocked.headers


def test_photo_origin_rejects_non_https_and_csp_injection(monkeypatch):
    monkeypatch.setenv("PHOTO_URL_ORIGIN", "https://images.example")
    assert api_main._photo_origin() == "https://images.example"
    monkeypatch.setenv("PHOTO_URL_ORIGIN", "http://images.example")
    with pytest.raises(ValueError, match="HTTPS origin"):
        api_main._photo_origin()
    monkeypatch.setenv("PHOTO_URL_ORIGIN", "https://images.example; script-src *")
    with pytest.raises(ValueError, match="HTTPS origin"):
        api_main._photo_origin()


def test_rate_limit_is_bounded_and_returns_429(client, monkeypatch):
    api_main._rate_requests.clear()
    monkeypatch.setattr(api_main, "RATE_LIMIT_REQUESTS", 1)
    assert client.get("/players/search", params={"q": "a"}).status_code == 200
    response = client.get("/players/search", params={"q": "a"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    assert response.headers["x-content-type-options"] == "nosniff"
    api_main._rate_requests.clear()


@pytest.mark.parametrize("path", [
    "/..%2f..%2fetc/passwd",
    "/%2e%2e/",
    "/%2e%2e%2f..%2fetc%2fpasswd",
    "/%252e%252e%252f..%252fetc%252fpasswd",
])
def test_spa_fallback_never_serves_files_outside_dist(client, monkeypatch, tmp_path, path):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>safe app</html>", encoding="utf-8")
    outside = tmp_path / "etc"
    outside.mkdir()
    (outside / "passwd").write_text("outside-secret-marker", encoding="utf-8")
    monkeypatch.setattr(api_main, "DIST", dist)

    response = client.get(path)
    assert response.status_code == 200
    assert "outside-secret-marker" not in response.text
    assert "safe app" in response.text


def test_failed_analytics_build_is_not_retried(client, monkeypatch):
    store = make_store()
    attempts = 0

    def fail_build(_store):
        nonlocal attempts
        attempts += 1
        raise ValueError("private model path")

    monkeypatch.setattr(api_main, "Analytics", fail_build)
    api_main._build_failures.pop(id(store), None)
    with pytest.raises(ValueError):
        api_main._analytics(store)
    with pytest.raises(RuntimeError, match="previously failed"):
        api_main._analytics(store)
    assert attempts == 1
    api_main._build_failures.pop(id(store), None)


def test_real_data_smoke():
    store = load_store()
    assert len(store.players) > 5000
    top = store.search("haal", 1)[0]
    assert top["name"] == "Erling Haaland" and top["position"] == "Attack"


def test_rate_limit_ignores_health_and_static_paths(client, monkeypatch):
    """Page loads fetch many static files; only API calls may be limited."""
    api_main._rate_requests.clear()
    monkeypatch.setattr(api_main, "RATE_LIMIT_REQUESTS", 1)
    for _ in range(5):
        assert client.get("/health").status_code == 200
        assert client.get("/assets/does-not-exist.js").status_code != 429
    api_main._rate_requests.clear()


def test_null_byte_path_is_a_404_not_a_500(client):
    assert client.get("/%00").status_code in (404, 200)      # 200 only if the SPA fallback is mounted
    assert client.get("/assets/%00").status_code in (404, 200)
