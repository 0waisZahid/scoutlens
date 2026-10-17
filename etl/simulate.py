"""Synthetic player generator so the pipeline can be developed before real data.

IMPORTANT: the "true" value function here is something I made up. Scores on
simulated data only prove the code works, NOT that the model predicts real
Transfermarkt values. Swap in real data via etl/load.py as soon as you have it.
"""
import numpy as np
import pandas as pd

from core.schema import POSITIONS


def simulate_players(n: int = 4000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    pos = rng.choice(POSITIONS, n, p=[0.1, 0.35, 0.33, 0.22])
    age = np.clip(rng.normal(25.5, 4.2, n), 16, 40).round()
    tier = rng.choice([1, 2, 3, 4], n, p=[0.25, 0.3, 0.25, 0.2])  # 1 = top-5 league
    contract = np.clip(rng.normal(2.5, 1.3, n), 0, 6).round(1)
    height = np.clip(rng.normal(180, 6.5, n) + (pos == "GK") * 6, 160, 205).round()
    minutes = np.clip(rng.normal(1800, 800, n), 90, 3420).round()

    # latent quality drives stats
    quality = rng.normal(0, 1, n) - 0.35 * (tier - 1)
    atk = np.isin(pos, ["FW", "MF"]) * 1.0
    fw = (pos == "FW") * 1.0
    df = pd.DataFrame({
        "player_id": np.arange(n),
        "name": [f"Player {i}" for i in range(n)],
        "age": age, "position": pos, "league_tier": tier,
        "contract_years_left": contract, "height_cm": height, "minutes": minutes,
    })

    def stat(base, q_w, mask=1.0, noise=0.08):
        v = base * mask * np.exp(q_w * quality + rng.normal(0, 0.25, n))
        return np.round(v + rng.normal(0, noise, n).clip(-0.05), 3).clip(0)

    df["goals_p90"] = stat(0.15, 0.5, 0.2 + 1.2 * fw + 0.4 * atk)
    df["assists_p90"] = stat(0.10, 0.35, 0.3 + 0.8 * atk)
    df["xg_p90"] = stat(0.14, 0.45, 0.2 + 1.2 * fw + 0.4 * atk)
    df["xa_p90"] = stat(0.09, 0.35, 0.3 + 0.8 * atk)
    df["shots_p90"] = stat(1.2, 0.25, 0.3 + 1.2 * fw + 0.5 * atk)
    df["key_passes_p90"] = stat(1.0, 0.3, 0.4 + 0.8 * atk)
    df["progressive_passes_p90"] = stat(4.0, 0.25, 0.5 + 0.6 * (pos != "GK"))
    df["dribbles_won_p90"] = stat(1.0, 0.3, 0.3 + 0.9 * atk)
    df["tackles_p90"] = stat(1.5, 0.1, 0.4 + 1.0 * (pos == "DF"))
    df["interceptions_p90"] = stat(1.0, 0.1, 0.4 + 1.0 * (pos == "DF"))
    df["aerials_won_p90"] = stat(1.5, 0.1, 0.5 + 0.8 * (pos == "DF"))

    # made-up ground truth: log-value with age curve, tier, contract, quality
    log_v = (
        14.2
        - 0.032 * (age - 25.5) ** 2 / 2
        + 0.75 * quality
        - 0.45 * (tier - 1)
        + 0.10 * np.minimum(contract, 4)
        + 0.00015 * (minutes - 1800)
        + 0.15 * fw
        + rng.normal(0, 0.30, n)
    )
    df["market_value_eur"] = (np.exp(log_v) / 50_000).round() * 50_000
    df["market_value_eur"] = df["market_value_eur"].clip(lower=50_000)
    return df
