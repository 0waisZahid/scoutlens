"""Clean the Kaggle Transfermarkt data into the ScoutLens data contract."""
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/kaggle")
OUT = Path("data/processed")
LEAGUES = ["GB1", "ES1", "IT1", "L1", "FR1"]  # PL, La Liga, Serie A, Bundesliga, Ligue 1
MIN_MINUTES = 450       # assumption: below this a season is too small to trust
MAX_MATCH_MINUTES = 130  # assumption: longer than this is a data error


def season_of(dates: pd.Series) -> pd.Series:
    """Season starts in August: 2023-09-01 -> 2023, 2024-03-01 -> 2023."""
    return dates.dt.year.where(dates.dt.month >= 8, dates.dt.year - 1)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    players = pd.read_csv(
        RAW / "players.csv",
        usecols=["player_id", "name", "date_of_birth", "position", "sub_position",
                 "foot", "height_in_cm", "country_of_citizenship"],
        parse_dates=["date_of_birth"],
    )
    apps = pd.read_csv(
        RAW / "appearances.csv",
        usecols=["appearance_id", "player_id", "date", "competition_id",
                 "yellow_cards", "red_cards", "goals", "assists", "minutes_played"],
        parse_dates=["date"],
    )
    vals = pd.read_csv(
        RAW / "player_valuations.csv",
        usecols=["player_id", "date", "market_value_in_eur"],
        parse_dates=["date"],
    ).rename(columns={"market_value_in_eur": "value_eur"})

    # ---- 1. clean appearances ----
    n0 = len(apps)
    apps = apps.drop_duplicates("appearance_id")
    apps = apps.dropna(subset=["date", "minutes_played"])
    apps = apps[apps["minutes_played"].between(0, MAX_MATCH_MINUTES)]
    apps = apps[(apps["goals"] >= 0) & (apps["assists"] >= 0)]
    apps = apps[apps["competition_id"].isin(LEAGUES)]
    print(f"appearances: {n0} raw -> {len(apps)} after cleaning + league filter")

    # ---- 2. aggregate to player-seasons ----
    apps["season"] = season_of(apps["date"])
    agg = apps.groupby(["player_id", "season"]).agg(
        appearances=("appearance_id", "count"),
        minutes=("minutes_played", "sum"),
        goals=("goals", "sum"),
        assists=("assists", "sum"),
        yellow_cards=("yellow_cards", "sum"),
        red_cards=("red_cards", "sum"),
    )
    # main league = the league where the player played most minutes that season
    main_league = (
        apps.groupby(["player_id", "season", "competition_id"])["minutes_played"].sum()
        .reset_index()
        .sort_values("minutes_played", ascending=False)
        .drop_duplicates(["player_id", "season"])
        .set_index(["player_id", "season"])["competition_id"]
        .rename("league")
    )
    seasons = agg.join(main_league).reset_index()

    # ---- 3. minimum minutes + per-90 stats ----
    before = len(seasons)
    seasons = seasons[seasons["minutes"] >= MIN_MINUTES].copy()
    print(f"player-seasons: {before} -> {len(seasons)} after >= {MIN_MINUTES} minutes")
    for col in ["goals", "assists", "yellow_cards", "red_cards"]:
        seasons[f"{col}_per90"] = seasons[col] / seasons["minutes"] * 90

    # ---- 4. clean valuations ----
    vals = vals.dropna().drop_duplicates(["player_id", "date"])
    vals = vals[vals["value_eur"] > 0].sort_values(["player_id", "date"])
    vals["season"] = season_of(vals["date"])

    # value at the END of each season = the last valuation dated inside that season
    season_value = (
        vals.groupby(["player_id", "season"])
        .agg(value_eur=("value_eur", "last"), value_date=("date", "last"))
        .reset_index()
    )
    df = seasons.merge(season_value, on=["player_id", "season"], how="inner")

    # ---- 5. player info + age ----
    df = df.merge(players, on="player_id", how="left")
    df["age"] = ((df["value_date"] - df["date_of_birth"]).dt.days / 365.25).round(1)
    df = df.dropna(subset=["position", "age"])
    df = df[df["age"].between(15, 45)]

    cols = ["player_id", "name", "position", "sub_position", "league", "season", "age",
            "appearances", "minutes", "goals", "assists", "yellow_cards", "red_cards",
            "goals_per90", "assists_per90", "yellow_cards_per90", "red_cards_per90",
            "height_in_cm", "foot", "country_of_citizenship", "value_date", "value_eur"]
    df = df[cols].sort_values(["player_id", "season"])
    df.to_csv(OUT / "player_seasons.csv", index=False)

    # full cleaned value history for the players we kept
    history = vals[vals["player_id"].isin(df["player_id"])][["player_id", "date", "value_eur"]]
    history.to_csv(OUT / "market_values.csv", index=False)

    print(f"player_seasons.csv: {len(df)} rows, {df['player_id'].nunique()} players")
    print(f"market_values.csv:  {len(history)} rows")
    print(df["season"].value_counts().sort_index())


if __name__ == "__main__":
    main()