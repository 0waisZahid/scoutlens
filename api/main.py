"""ScoutLens REST API.

Run:  uvicorn api.main:app --reload      then open  http://127.0.0.1:8000/docs
"""
import os
import threading
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.service import SORTS, Analytics
from api.store import DataStore, load_store

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Build the models and feature tables in the background so the first request is fast."""
    def warm() -> None:
        try:
            _analytics(get_store())
        except Exception as e:                 # never stop the server from starting
            print(f"warm-up failed (will retry on first request): {e!r}")
    threading.Thread(target=warm, daemon=True).start()
    yield


app = FastAPI(
    title="ScoutLens API",
    version="0.2.0",
    description="Football player search, valuation, forecasts, explanations and analytics.",
    lifespan=lifespan,
)
# Development setting: lets a browser UI running on another port call this API.
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return load_store()


_build_lock = threading.Lock()
_built: dict[int, Analytics] = {}


def _analytics(store: DataStore) -> Analytics:
    """Build once. The lock matters: a page fires several requests at once, and without it each
    would build its own copy (several seconds of CPU each) while the others wait."""
    key = id(store)
    if key not in _built:
        with _build_lock:
            if key not in _built:
                _built[key] = Analytics(store)
    return _built[key]


def get_analytics(store: DataStore = Depends(get_store)) -> Analytics:
    """Models + feature tables. Built on first use (a couple of seconds), then cached."""
    return _analytics(store)


def known_player(player_id: int, svc: Analytics) -> None:
    if not svc.has_player(player_id):
        raise HTTPException(status_code=404, detail=f"Unknown player_id {player_id}")


class PlayerSummary(BaseModel):
    player_id: int
    name: str
    position: str
    league: str
    latest_season: int
    age: float
    latest_value_eur: float | None


@app.get("/health")
def health(store: DataStore = Depends(get_store)) -> dict:
    return {"status": "ok", "players": len(store.players)}


@app.get("/meta")
def meta(svc: Analytics = Depends(get_analytics)) -> dict:
    """Seasons, leagues, positions and the available rankings (for building filters)."""
    return svc.meta()


@app.get("/players/search", response_model=list[PlayerSummary])
def search_players(
    q: str = Query(..., min_length=1, description="Start of a first name or surname"),
    limit: int = Query(10, ge=1, le=50),
    store: DataStore = Depends(get_store),
) -> list[dict]:
    """Autocomplete: matching players, most valuable first."""
    return store.search(q, limit)


@app.get("/players/{player_id}")
def player_profile(player_id: int, svc: Analytics = Depends(get_analytics)) -> dict:
    """Profile: bio, season-by-season stats, market value history, trend and percentiles."""
    known_player(player_id, svc)
    return svc.profile(player_id)


@app.get("/players/{player_id}/valuation")
def player_valuation(
    player_id: int,
    season: int | None = Query(None, description="Defaults to the player's latest season"),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    """Model value with an 80% range, SHAP-style factor breakdown and next-season forecast."""
    known_player(player_id, svc)
    try:
        return svc.valuation(player_id, season)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e.args[0]))


@app.get("/players/{player_id}/similar")
def similar_players(
    player_id: int,
    k: int = Query(6, ge=1, le=20),
    scope: Literal["active", "all"] = Query("active", description="active = current season only"),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    known_player(player_id, svc)
    return {"in_pool": svc.in_similarity_pool(player_id, scope), "players": svc.similar(player_id, k, scope)}


@app.get("/players/{player_id}/teammates")
def player_teammates(
    player_id: int,
    season: int | None = None,
    limit: int = Query(12, ge=1, le=50),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    known_player(player_id, svc)
    return svc.teammates(player_id, season, limit)


@app.get("/connections")
def connections(a: int, b: int, svc: Analytics = Depends(get_analytics)) -> dict:
    """Shortest chain of teammates between two players (like six degrees of Kevin Bacon)."""
    known_player(a, svc)
    known_player(b, svc)
    return svc.connection(a, b)


@app.get("/rankings")
def rankings(
    sort: str = Query("value", description=f"One of: {', '.join(SORTS)}"),
    season: int | None = None,
    position: Literal["FW", "MF", "DF", "GK"] | None = None,
    league: Literal["GB1", "ES1", "IT1", "L1", "FR1"] | None = None,
    min_age: float | None = Query(None, ge=15, le=50),
    max_age: float | None = Query(None, ge=15, le=50),
    min_minutes: int | None = Query(None, ge=0),
    min_value: float | None = Query(None, ge=0, description="EUR. Defaults depend on the sort"),
    max_value: float | None = Query(None, ge=0, description="EUR. Defaults depend on the sort"),
    limit: int = Query(25, ge=1, le=100),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    """Top players by market value, model gap, forecast or stats (heap-based top-k)."""
    if sort not in SORTS:
        raise HTTPException(status_code=422, detail=f"sort must be one of {list(SORTS)}")
    try:
        return svc.rankings(sort, season, position, league, min_age, max_age, min_minutes,
                            min_value, max_value, limit)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e.args[0]))


@app.get("/model/info")
def model_info(svc: Analytics = Depends(get_analytics)) -> dict:
    """Accuracy numbers, data coverage and what drives valuations overall."""
    return svc.model_info()


# --- production: serve the built frontend from the same service (no CORS, one URL) -------------
DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (DIST / "index.html").is_file():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Any other URL is a page of the single-page app (client-side routing)."""
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
