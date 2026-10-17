"""Load player data. Real datasets get mapped to core.schema columns here."""
from __future__ import annotations
from pathlib import Path

import pandas as pd

from core.schema import REQUIRED
from etl.simulate import simulate_players

ROOT = Path(__file__).resolve().parent.parent


def load_players(path: str | None = None) -> pd.DataFrame:
    """Load a CSV with the schema columns, or fall back to simulated data."""
    if path:
        df = pd.read_csv(path)
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            raise ValueError(f"CSV is missing columns: {missing}")
        return df
    sim = ROOT / "data" / "simulated" / "players.csv"
    if sim.exists():
        return pd.read_csv(sim)
    df = simulate_players()
    sim.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(sim, index=False)
    return df
