"""Core data classes for ScoutLens."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class MarketValueRecord:
    """One dated market value for a player."""
    date: date
    value_eur: float

    def __post_init__(self) -> None:
        if self.value_eur <= 0:
            raise ValueError("value_eur must be positive")


@dataclass
class PerformanceRecord:
    """One player's statistics for one season."""
    season: int
    minutes: int
    goals: int
    assists: int
    appearances: int = 0

    def __post_init__(self) -> None:
        if self.minutes < 0 or self.goals < 0 or self.assists < 0:
            raise ValueError("minutes, goals and assists cannot be negative")

    def per90(self, stat: str) -> float:
        """Return goals or assists per 90 minutes (0 if the player has no minutes)."""
        if stat not in ("goals", "assists"):
            raise ValueError("stat must be 'goals' or 'assists'")
        if self.minutes == 0:
            return 0.0
        return getattr(self, stat) / self.minutes * 90


@dataclass
class Player:
    """A player with a profile, season stats and value history."""
    player_id: int
    name: str
    position: str
    birth_date: date | None = None
    seasons: list[PerformanceRecord] = field(default_factory=list)
    values: list[MarketValueRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name cannot be empty")

    def age(self, on: date | None = None) -> float | None:
        """Age in years on a given date (today by default)."""
        if self.birth_date is None:
            return None
        on = on or date.today()
        return round((on - self.birth_date).days / 365.25, 1)

    def latest_season(self) -> PerformanceRecord | None:
        return max(self.seasons, key=lambda s: s.season, default=None)

    def latest_value(self) -> float | None:
        if not self.values:
            return None
        return max(self.values, key=lambda v: v.date).value_eur

    def value_change_since(self, since: date) -> float | None:
        """Percent change in value from the last record on/before `since` to the latest."""
        older = [v for v in self.values if v.date <= since]
        if not older or not self.values:
            return None
        start = max(older, key=lambda v: v.date).value_eur
        return (self.latest_value() - start) / start * 100
