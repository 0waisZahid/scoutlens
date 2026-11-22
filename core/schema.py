"""Column schema shared by every data source.

Any real dataset (Transfermarkt export, FBref scrape, Kaggle CSV...) just needs
to be mapped to these column names in etl/ and the rest of the pipeline works.
"""

TARGET = "market_value_eur"

ID_COLS = ["player_id", "name"]

# Context features
CONTEXT = ["age", "position", "league_tier", "contract_years_left", "height_cm"]

# Per-90 performance features (from FBref / Opta / StatsBomb / WhoScored...)
PERFORMANCE = [
    "minutes",
    "goals_p90",
    "assists_p90",
    "xg_p90",
    "xa_p90",
    "shots_p90",
    "key_passes_p90",
    "progressive_passes_p90",
    "dribbles_won_p90",
    "tackles_p90",
    "interceptions_p90",
    "aerials_won_p90",
]

POSITIONS = ["GK", "DF", "MF", "FW"]

REQUIRED = [TARGET] + CONTEXT + PERFORMANCE
