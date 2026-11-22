"""Add each player-season's main club (most minutes played) to player_seasons.csv."""
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/kaggle")
PROC = Path("data/processed")
LEAGUES = ["GB1", "ES1", "IT1", "L1", "FR1"]

apps = pd.read_csv(
    RAW / "appearances.csv",
    usecols=["player_id", "date", "player_club_id", "competition_id", "minutes_played"],
    parse_dates=["date"],
)
apps = apps[apps["competition_id"].isin(LEAGUES)]
apps = apps.dropna(subset=["date", "minutes_played", "player_club_id"])
apps = apps[apps["minutes_played"].between(0, 130)]
apps["season"] = apps["date"].dt.year.where(apps["date"].dt.month >= 8, apps["date"].dt.year - 1)

club = (
    apps.groupby(["player_id", "season", "player_club_id"])["minutes_played"].sum()
    .reset_index()
    .sort_values("minutes_played", ascending=False)
    .drop_duplicates(["player_id", "season"])
    .rename(columns={"player_club_id": "club_id"})[["player_id", "season", "club_id"]]
)

ps = pd.read_csv(PROC / "player_seasons.csv")
out = ps.merge(club, on=["player_id", "season"], how="left")
print("rows:", len(out), "| missing club:", out["club_id"].isna().sum())
out.to_csv(PROC / "player_seasons_club.csv", index=False)
