"""ScoutLens REST API.

Run:  uvicorn api.main:app --reload      then open  http://127.0.0.1:8000/docs
"""
from functools import lru_cache

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.store import DataStore, load_store

app = FastAPI(
    title="ScoutLens API",
    version="0.1.0",
    description="Football player search, valuation and analytics.",
)
# Development setting: lets a browser UI running on another port call this API.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return load_store()


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


@app.get("/players/search", response_model=list[PlayerSummary])
def search_players(
    q: str = Query(..., min_length=1, description="Start of a first name or surname"),
    limit: int = Query(10, ge=1, le=50),
    store: DataStore = Depends(get_store),
) -> list[dict]:
    """Autocomplete: matching players, most valuable first."""
    return store.search(q, limit)
