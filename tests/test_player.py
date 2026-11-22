from datetime import date

import pytest

from core.player import MarketValueRecord, PerformanceRecord, Player


def test_per90_goals_and_assists():
    rec = PerformanceRecord(season=2023, minutes=900, goals=10, assists=5)
    assert rec.per90("goals") == pytest.approx(1.0)
    assert rec.per90("assists") == pytest.approx(0.5)


def test_per90_zero_minutes_returns_zero():
    rec = PerformanceRecord(season=2023, minutes=0, goals=0, assists=0)
    assert rec.per90("goals") == 0.0


def test_per90_rejects_unknown_stat():
    rec = PerformanceRecord(season=2023, minutes=900, goals=1, assists=1)
    with pytest.raises(ValueError):
        rec.per90("tackles")


def test_negative_stats_rejected():
    with pytest.raises(ValueError):
        PerformanceRecord(season=2023, minutes=-1, goals=0, assists=0)


def test_market_value_must_be_positive():
    with pytest.raises(ValueError):
        MarketValueRecord(date=date(2023, 1, 1), value_eur=0)


def test_player_name_cannot_be_empty():
    with pytest.raises(ValueError):
        Player(player_id=1, name="   ", position="FW")


def test_age():
    p = Player(player_id=1, name="Test Player", position="FW", birth_date=date(2000, 1, 1))
    assert p.age(on=date(2025, 1, 1)) == 25.0


def test_age_unknown_birth_date():
    assert Player(player_id=1, name="Test Player", position="FW").age() is None


def test_latest_season_picks_highest_year():
    p = Player(player_id=1, name="Test Player", position="FW", seasons=[
        PerformanceRecord(2021, 900, 1, 1),
        PerformanceRecord(2023, 900, 3, 2),
        PerformanceRecord(2022, 900, 2, 2),
    ])
    assert p.latest_season().season == 2023


def test_latest_value_and_change():
    p = Player(player_id=1, name="Test Player", position="FW", values=[
        MarketValueRecord(date(2022, 1, 1), 10_000_000),
        MarketValueRecord(date(2024, 1, 1), 20_000_000),
        MarketValueRecord(date(2023, 1, 1), 15_000_000),
    ])
    assert p.latest_value() == 20_000_000
    # last value on or before 2023-06-01 is 15M, so the change to 20M is +33.3%
    assert p.value_change_since(date(2023, 6, 1)) == pytest.approx(33.333, rel=1e-3)
    assert p.value_change_since(date(2021, 1, 1)) is None


def test_no_values_returns_none():
    p = Player(player_id=1, name="Test Player", position="FW")
    assert p.latest_value() is None
