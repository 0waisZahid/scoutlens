"""In-memory data store for the API.

Loads the cleaned CSVs once at start-up and builds:
  * a Player object (core.player) for every player, with season stats and value history
  * a trie (core.trie) over all player names, for fast autocomplete
  * the latest known market value of each player, so search results can be ranked

The API only reads from this store, so there is no database yet. Moving to SQLite or
PostgreSQL later only means replacing this file.
"""
from pathlib import Path

import pandas as pd

from core.heap import top_k
from core.player import MarketValueRecord, PerformanceRecord, Player
from core.trie import Trie

ROOT = Path(__file__).resolve().parent.parent
SEASONS_CSV = ROOT / "data" / "processed" / "player_seasons_club.csv"
VALUES_CSV = ROOT / "data" / "processed" / "market_values.csv"


class DataStore:
    def __init__(self, seasons: pd.DataFrame, values: pd.DataFrame) -> None:
        seasons = seasons.dropna(subset=["name"]).sort_values(["player_id", "season"])
        values = values.assign(date=pd.to_datetime(values["date"])).sort_values(["player_id", "date"])

        self.players: dict[int, Player] = {}
        self.latest_row: dict[int, dict] = {}          # newest season row per player
        self.latest_value: dict[int, float | None] = {}
        self.trie = Trie()

        # One pass over the rows (sorted by player, then season), so the last row seen
        # for a player is his newest season.
        fields = ["player_id", "name", "position", "league", "season", "age",
                  "minutes", "goals", "assists", "appearances"]
        for pid, name, position, league, season, age, minutes, goals, assists, apps in zip(
                *(seasons[f].tolist() for f in fields)):
            pid = int(pid)
            player = self.players.get(pid)
            if player is None:
                player = self.players[pid] = Player(player_id=pid, name=str(name), position=str(position))
            player.name, player.position = str(name), str(position)
            player.seasons.append(PerformanceRecord(
                season=int(season), minutes=int(minutes), goals=int(goals),
                assists=int(assists), appearances=int(apps)))
            self.latest_row[pid] = {"league": league, "season": season, "age": age}

        for pid, player in self.players.items():
            self.trie.insert(player.name, pid)

        known = values[values["player_id"].isin(set(self.players))]
        for pid, day, value in zip(known["player_id"].tolist(), known["date"].tolist(), known["value_eur"].tolist()):
            self.players[int(pid)].values.append(MarketValueRecord(date=day.date(), value_eur=float(value)))
        for pid, player in self.players.items():
            self.latest_value[pid] = player.values[-1].value_eur if player.values else None

    def summary(self, player_id: int) -> dict:
        row = self.latest_row[player_id]
        return {
            "player_id": player_id,
            "name": self.players[player_id].name,
            "position": self.players[player_id].position,
            "league": str(row["league"]),
            "latest_season": int(row["season"]),
            "age": float(row["age"]),
            "latest_value_eur": self.latest_value[player_id],
        }

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Players whose name (or any word of it) starts with the query, most valuable first."""
        matches = self.trie.search_prefix(query)                       # all matches
        best = top_k(matches, limit, key=lambda m: self.latest_value.get(m[1]) or 0.0)   # heap, O(m log k)
        return [self.summary(pid) for _, pid in best]


def load_store() -> DataStore:
    return DataStore(pd.read_csv(SEASONS_CSV), pd.read_csv(VALUES_CSV))
