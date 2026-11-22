"""ScoutLens REST API.

Run:  uvicorn api.main:app --reload      then open  http://127.0.0.1:8000/docs
"""
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Path as ApiPath, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.service import SORTS, Analytics
from api.store import DataStore, load_store

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Build the models and feature tables in the background so the first request is fast."""
    def warm() -> None:
        try:
            svc = _analytics(get_store())
            svc.season_frame(svc.max_season)       # the home page needs it straight away
        except Exception as e:                 # never stop the server from starting
            print(f"warm-up failed; restart after fixing the cause: {e!r}")
    threading.Thread(target=warm, daemon=True).start()
    yield


app = FastAPI(
    title="ScoutLens API",
    version="0.2.0",
    description="Football player search, valuation, forecasts, explanations and analytics.",
    docs_url=None if os.getenv("ENV", "").lower() == "production" else "/docs",
    redoc_url=None if os.getenv("ENV", "").lower() == "production" else "/redoc",
    openapi_url=None if os.getenv("ENV", "").lower() == "production" else "/openapi.json",
    lifespan=lifespan,
)

_production = os.getenv("ENV", "").lower() == "production"
_configured_origins = os.getenv("ALLOWED_ORIGINS")
if _configured_origins is None:
    _allowed_origins = [] if _production else ["http://localhost:5173"]
else:
    _allowed_origins = [origin.strip() for origin in _configured_origins.split(",") if origin.strip()]
if "*" in _allowed_origins:
    raise ValueError("ALLOWED_ORIGINS must not contain '*'.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_REQUESTS = 240
# Only API calls are counted. Page loads and static files (/, /assets, fonts) are not: one page view
# fetches ~17 files, and counting them locked real users out (and a whole site, behind a shared proxy IP).
RATE_LIMITED_PREFIXES = ("/players", "/rankings", "/connections", "/model", "/meta")
RATE_LIMIT_MAX_CLIENTS = 4096
_rate_lock = threading.Lock()
_rate_requests: dict[str, deque[float]] = defaultdict(deque)


def _photo_origin() -> str | None:
    configured = os.getenv("PHOTO_URL_ORIGIN")
    if not configured:
        return None
    parsed = urlsplit(configured)
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("PHOTO_URL_ORIGIN must be an HTTPS origin without a path.") from None
    if (
        parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
        or parsed.password is not None or (port is not None and not 1 <= port <= 65535)
        or not re.fullmatch(r"[A-Za-z0-9.\-\[\]:]+", parsed.netloc)
        or parsed.path not in ("", "/") or parsed.query or parsed.fragment
    ):
        raise ValueError("PHOTO_URL_ORIGIN must be an HTTPS origin without a path.")
    return f"https://{parsed.netloc}"


_photo_origin_value = _photo_origin()
_csp = "; ".join((
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    f"img-src 'self' data:{' ' + _photo_origin_value if _photo_origin_value else ''}",
    "font-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))


def _is_rate_limited(client_ip: str, now: float) -> bool:
    with _rate_lock:
        if client_ip not in _rate_requests and len(_rate_requests) >= RATE_LIMIT_MAX_CLIENTS:
            oldest = min(_rate_requests, key=lambda ip: _rate_requests[ip][-1] if _rate_requests[ip] else 0)
            del _rate_requests[oldest]
        requests = _rate_requests[client_ip]
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if len(requests) >= RATE_LIMIT_REQUESTS:
            return True
        requests.append(now)
        return False


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    if request.method == "GET" and request.url.path.startswith(RATE_LIMITED_PREFIXES) and _is_rate_limited(ip, time.monotonic()):
        response = JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})
    else:
        response = await call_next(request)
    response.headers["Content-Security-Policy"] = _csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return load_store()


_build_lock = threading.Lock()
_built: dict[int, Analytics] = {}
_build_failures: dict[int, bool] = {}
_MAX_ANALYTICS_INSTANCES = 2


def _analytics(store: DataStore) -> Analytics:
    """Build once. The lock matters: a page fires several requests at once, and without it each
    would build its own copy (several seconds of CPU each) while the others wait."""
    key = id(store)
    with _build_lock:
        if key in _build_failures:
            raise RuntimeError("Analytics initialization previously failed.")
        if key in _built:
            return _built[key]
        try:
            analytics = Analytics(store)
        except Exception:
            logging.exception("Analytics initialization failed.")
            _build_failures[key] = True
            while len(_build_failures) > _MAX_ANALYTICS_INSTANCES:
                del _build_failures[next(iter(_build_failures))]
            raise
        _built[key] = analytics
        while len(_built) > _MAX_ANALYTICS_INSTANCES:
            del _built[next(iter(_built))]
        return analytics


def get_analytics(store: DataStore = Depends(get_store)) -> Analytics:
    """Models + feature tables. Built on first use (a couple of seconds), then cached."""
    try:
        return _analytics(store)
    except Exception:
        raise HTTPException(status_code=503, detail="Analytics are temporarily unavailable.") from None


def known_player(player_id: int, svc: Analytics) -> None:
    if not svc.has_player(player_id):
        raise HTTPException(status_code=404, detail="Player not found.")


class PlayerSummary(BaseModel):
    player_id: int
    name: str
    position: str
    league: str
    latest_season: int
    age: float
    latest_value_eur: float | None


@app.get("/health")
@app.head("/health")
def health(store: DataStore = Depends(get_store)) -> dict:
    return {"status": "ok", "players": len(store.players)}


@app.get("/meta")
def meta(svc: Analytics = Depends(get_analytics)) -> dict:
    """Seasons, leagues, positions and the available rankings (for building filters)."""
    return svc.meta()


@app.get("/players/search", response_model=list[PlayerSummary])
def search_players(
    q: str = Query(..., min_length=1, max_length=100, description="Start of a first name or surname"),
    limit: int = Query(10, ge=1, le=50),
    store: DataStore = Depends(get_store),
) -> list[dict]:
    """Autocomplete: matching players, most valuable first."""
    return store.search(q, limit)


@app.get("/players/{player_id}")
def player_profile(
    player_id: int = ApiPath(ge=1, le=2_147_483_647),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    """Profile: bio, season-by-season stats, market value history, trend and percentiles."""
    known_player(player_id, svc)
    return svc.profile(player_id)


@app.get("/players/{player_id}/valuation")
def player_valuation(
    player_id: int = ApiPath(ge=1, le=2_147_483_647),
    season: int | None = Query(None, ge=1900, le=2100, description="Defaults to the player's latest season"),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    """Model value with an 80% range, SHAP-style factor breakdown and next-season forecast."""
    known_player(player_id, svc)
    try:
        return svc.valuation(player_id, season)
    except KeyError:
        raise HTTPException(status_code=404, detail="No data for the requested player and season.")


@app.get("/players/{player_id}/model-history")
def model_history(
    player_id: int = ApiPath(ge=1, le=2_147_483_647),
    svc: Analytics = Depends(get_analytics),
) -> list[dict]:
    """Model value and 80% range for each season, beside the market value (in_sample marks training seasons)."""
    known_player(player_id, svc)
    return svc.model_history(player_id)


@app.get("/players/{player_id}/similar")
def similar_players(
    player_id: int = ApiPath(ge=1, le=2_147_483_647),
    k: int = Query(6, ge=1, le=20),
    scope: Literal["active", "all"] = Query("active", description="active = current season only"),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    known_player(player_id, svc)
    return {"in_pool": svc.in_similarity_pool(player_id, scope), "players": svc.similar(player_id, k, scope)}


@app.get("/players/{player_id}/teammates")
def player_teammates(
    player_id: int = ApiPath(ge=1, le=2_147_483_647),
    season: int | None = Query(None, ge=1900, le=2100),
    limit: int = Query(12, ge=1, le=50),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    known_player(player_id, svc)
    return svc.teammates(player_id, season, limit)


@app.get("/connections")
def connections(
    a: int = Query(..., ge=1, le=2_147_483_647),
    b: int = Query(..., ge=1, le=2_147_483_647),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    """Shortest chain of teammates between two players (like six degrees of Kevin Bacon)."""
    known_player(a, svc)
    known_player(b, svc)
    return svc.connection(a, b)


@app.get("/rankings")
def rankings(
    sort: str = Query("value", description=f"One of: {', '.join(SORTS)}"),
    season: int | None = Query(None, ge=1900, le=2100),
    position: Literal["FW", "MF", "DF", "GK"] | None = None,
    league: Literal["GB1", "ES1", "IT1", "L1", "FR1"] | None = None,
    min_age: float | None = Query(None, ge=15, le=50, allow_inf_nan=False),
    max_age: float | None = Query(None, ge=15, le=50, allow_inf_nan=False),
    min_minutes: int | None = Query(None, ge=0, le=200_000),
    min_value: float | None = Query(None, ge=0, le=1e12, allow_inf_nan=False, description="EUR. Defaults depend on the sort"),
    max_value: float | None = Query(None, ge=0, le=1e12, allow_inf_nan=False, description="EUR. Defaults depend on the sort"),
    limit: int = Query(25, ge=1, le=100),
    svc: Analytics = Depends(get_analytics),
) -> dict:
    """Top players by market value, model gap, forecast or stats (heap-based top-k)."""
    if sort not in SORTS:
        raise HTTPException(status_code=422, detail="Unsupported ranking sort.")
    if min_age is not None and max_age is not None and min_age > max_age:
        raise HTTPException(status_code=422, detail="min_age must not exceed max_age.")
    if min_value is not None and max_value is not None and min_value > max_value:
        raise HTTPException(status_code=422, detail="min_value must not exceed max_value.")
    try:
        return svc.rankings(sort, season, position, league, min_age, max_age, min_minutes,
                            min_value, max_value, limit)
    except KeyError:
        raise HTTPException(status_code=404, detail="No data for the requested season.")


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
    from fastapi.responses import FileResponse

    if "\x00" in path:                      # a null byte makes pathlib raise ValueError (was a 500)
        raise HTTPException(status_code=404, detail="Not Found")
    try:
        dist = DIST.resolve()
        index = dist / "index.html"
        f = (dist / path).resolve()
        is_file = path and f.is_file() and dist in f.parents
    except (ValueError, OSError):
        raise HTTPException(status_code=404, detail="Not Found") from None
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    if is_file:
        return FileResponse(f)
    return FileResponse(index)
