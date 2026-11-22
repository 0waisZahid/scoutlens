"""Analytics layer for the API: valuations, ranges, forecasts, explanations, rankings,
similar players and the teammate graph.

It wraps the saved models in models/ and the from-scratch structures in core/:

  * rankings        -> core.heap.top_k            (O(n log k), no full sort)
  * similar players -> core.similarity            (z-scores + position index + heap)
  * teammates       -> core.graph.FootballGraph   (BFS)
  * value trend     -> core.timeseries            (least squares, exponential smoothing)

Everything heavy is computed once at start-up or lazily per season and cached, so each
request is cheap. The API only reads from this object.
"""
from __future__ import annotations

import math
import threading
from pathlib import Path

import numpy as np
import pandas as pd

import ml.explain as ex
import ml.forecast as fc
import ml.train_and_tune as tt
import ml.uncertainty as un
from api.store import DataStore
from core.graph import FootballGraph
from core.heap import top_k
from core.similarity import SimilarityEngine
from core.timeseries import exponential_smoothing, linear_trend

ROOT = Path(__file__).resolve().parent.parent
CLUBS_CSV = ROOT / "data" / "processed" / "clubs.csv"      # optional: club_id,name

POSITION_LABEL = {"FW": "Attack", "MF": "Midfield", "DF": "Defender", "GK": "Goalkeeper"}
LEAGUE_LABEL = {"GB1": "Premier League", "ES1": "La Liga", "IT1": "Serie A",
                "L1": "Bundesliga", "FR1": "Ligue 1"}
TEST_FROM = tt.TEST_FROM            # seasons from here on were never seen by the models

# ranking name -> (column, descending?, label, needs a minimum of minutes?)
SORTS: dict[str, tuple[str, bool, str, bool]] = {
    "value": ("market_value_eur", True, "Most valuable", False),
    "undervalued": ("gap_pct", True, "Model says undervalued", True),
    "overvalued": ("gap_pct", False, "Model says overvalued", True),
    "risers": ("forecast_change_pct", True, "Projected risers", True),
    "fallers": ("forecast_change_pct", False, "Projected fallers", True),
    "goals": ("goals", True, "Most goals", False),
    "assists": ("assists", True, "Most assists", False),
    "goals_p90": ("goals_per90", True, "Goals per 90", True),
    "assists_p90": ("assists_per90", True, "Assists per 90", True),
    "minutes": ("minutes", True, "Most minutes", False),
    "young": ("market_value_eur", True, "Most valuable under 21", False),
}

# Where the model is trustworthy enough to rank on its gap / forecast: below EUR 2M ranges are
# unreliable (README), above EUR 100M the valuation is compressed. Overridable per request.
VALUE_BANDS: dict[str, tuple[float | None, float | None]] = {
    "undervalued": (2e6, 100e6), "overvalued": (2e6, 100e6),
    "risers": (1e6, None), "fallers": (1e6, None),
}

RADAR_METRICS = [("goals_per90", "Goals / 90"), ("assists_per90", "Assists / 90"),
                 ("minutes", "Minutes"), ("appearances", "Appearances"),
                 ("market_value_eur", "Value"), ("discipline", "Discipline")]


def num(x, nd: int | None = None):
    """JSON-safe number: NaN / inf / missing -> None."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd) if nd is not None else f


def text(x) -> str | None:
    return None if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x) else str(x)


class Analytics:
    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.p, _ = tt.load_prepared()
        self.max_season = int(self.p["season"].max())
        self.val_bundle = tt.load_bundle()
        self.range_bundle = un.load()
        self.fc_bundle = fc.load()

        self.by_player = {int(pid): g.sort_values("season") for pid, g in self.p.groupby("player_id")}
        self.latest = self.by_player_latest()
        self.perc = self._percentiles()
        self.clubs = self._load_clubs()
        self.football_graph = FootballGraph.from_rows(
            zip(self.p["player_id"].astype(int), self.p["club_id"].astype(int), self.p["season"].astype(int)))
        self._frames: dict[int, pd.DataFrame] = {}
        self._engines: dict[str, SimilarityEngine] = {}
        self._global: list | None = None
        self._lock = threading.RLock()   # several requests can arrive at once: compute each cache entry once

    # ------------------------------------------------------------------ set-up
    def by_player_latest(self) -> pd.DataFrame:
        return self.p.sort_values(["player_id", "season"]).groupby("player_id").tail(1).set_index("player_id")

    def _percentiles(self) -> pd.DataFrame:
        """Percentile (0-100) of each player-season among same-position players that season
        with at least 450 minutes. NaN for players under 450 minutes."""
        p = self.p
        out = pd.DataFrame(index=p.index, columns=[m for m, _ in RADAR_METRICS], dtype=float)
        elig = p[p["minutes"] >= 450]
        grp = elig.groupby(["season", "position"])
        for col, _ in RADAR_METRICS:
            if col == "discipline":
                cards = elig["yellow_cards_per90"] + 3 * elig["red_cards_per90"]
                out.loc[elig.index, col] = 100 - (cards.groupby([elig["season"], elig["position"]]).rank(pct=True) * 100)
            else:
                out.loc[elig.index, col] = grp[col].rank(pct=True) * 100
        return out

    def _load_clubs(self) -> dict[int, str]:
        """Club names are not in the cleaned data. If data/processed/clubs.csv exists
        (club_id + name or pretty_name, e.g. from the Kaggle Transfermarkt clubs.csv), use it."""
        if not CLUBS_CSV.exists():
            return {}
        df = pd.read_csv(CLUBS_CSV)
        col = next((c for c in ("pretty_name", "name") if c in df.columns), None)
        if col is None or "club_id" not in df.columns:
            return {}
        return {int(i): str(n) for i, n in zip(df["club_id"], df[col]) if pd.notna(n)}

    def club_name(self, club_id) -> str | None:
        return self.clubs.get(int(club_id)) if club_id is not None and not pd.isna(club_id) else None

    # --------------------------------------------------------------- lookups
    def has_player(self, player_id: int) -> bool:
        return player_id in self.by_player

    def _row(self, player_id: int, season: int | None = None) -> pd.DataFrame:
        g = self.by_player[player_id]
        if season is None:
            return g.tail(1)
        r = g[g["season"] == season]
        if r.empty:
            raise KeyError(f"no data for player {player_id} in season {season}")
        return r

    def card(self, player_id: int) -> dict:
        """Compact player card (latest season) used in lists."""
        r = self.latest.loc[player_id]
        return {
            "player_id": int(player_id), "name": str(r["name"]),
            "position": POSITION_LABEL.get(r["position"], str(r["position"])),
            "position_code": str(r["position"]), "sub_position": text(r["sub_position"]),
            "league": str(r["league"]), "club_id": int(r["club_id"]), "club_name": self.club_name(r["club_id"]),
            "season": int(r["season"]), "age": num(r["age"], 1),
            "minutes": int(r["minutes"]), "goals": int(r["goals"]), "assists": int(r["assists"]),
            "market_value_eur": num(r["market_value_eur"]),
        }

    # ------------------------------------------------------------------ profile
    def profile(self, player_id: int) -> dict:
        g = self.by_player[player_id]
        last = g.iloc[-1]
        seasons = [{
            "season": int(r.season), "age": num(r.age, 1), "league": str(r.league), "club_id": int(r.club_id),
            "club_name": self.club_name(r.club_id), "appearances": int(r.appearances), "minutes": int(r.minutes),
            "goals": int(r.goals), "assists": int(r.assists), "goals_per90": num(r.goals_per90, 2),
            "assists_per90": num(r.assists_per90, 2), "yellow_cards": int(r.yellow_cards),
            "red_cards": int(r.red_cards), "market_value_eur": num(r.market_value_eur),
        } for r in g.itertuples()]

        player = self.store.players.get(player_id)
        history = [{"date": v.date.isoformat(), "value_eur": v.value_eur} for v in player.values] if player else []
        perc = self.perc.loc[g.index[-1]]
        percentiles = {m: num(perc[m], 0) for m, _ in RADAR_METRICS}

        card = self.card(player_id)
        card.update({
            "country": text(last["country_of_citizenship"]), "foot": text(last["foot"]),
            "height_cm": num(last["height_in_cm"], 0), "first_season": int(g["season"].min()),
            "is_active": int(last["season"]) == self.max_season,
        })
        return {**card, "seasons": seasons, "value_history": history, "trend": self._trend(player, g),
                "percentiles": percentiles, "radar_labels": {m: lbl for m, lbl in RADAR_METRICS}}

    def _trend(self, player, g: pd.DataFrame) -> dict:
        out = {"value_change_12m_pct": None, "annual_growth_pct": None, "peak_value_eur": None,
               "peak_date": None, "form_goals_p90": None, "form_assists_p90": None}
        if player and player.values:
            latest = max(player.values, key=lambda v: v.date)
            peak = max(player.values, key=lambda v: v.value_eur)
            out["peak_value_eur"], out["peak_date"] = peak.value_eur, peak.date.isoformat()
            ch = player.value_change_since(latest.date.replace(year=latest.date.year - 1))
            out["value_change_12m_pct"] = num(ch, 1)
            recent = [v for v in player.values if (latest.date - v.date).days <= 3 * 365]
            if len(recent) >= 3:
                years = [v.date.toordinal() / 365.25 for v in recent]
                try:
                    slope, _ = linear_trend([math.log(v.value_eur) for v in recent], years)
                    out["annual_growth_pct"] = num((math.exp(slope) - 1) * 100, 1)
                except ValueError:
                    pass
        played = g[g["minutes"] >= 450]
        if len(played) >= 1:                       # exponentially smoothed form: recent seasons count more
            out["form_goals_p90"] = num(exponential_smoothing(played["goals_per90"].tolist(), 0.6)[-1], 2)
            out["form_assists_p90"] = num(exponential_smoothing(played["assists_per90"].tolist(), 0.6)[-1], 2)
        return out

    # ---------------------------------------------------------------- valuation
    def valuation(self, player_id: int, season: int | None = None) -> dict:
        row = self._row(player_id, season)
        r = row.iloc[0]
        season = int(r["season"])
        market = float(r["market_value_eur"])

        point = float(tt.predict_values(self.val_bundle, row)[0])
        iv = un.predict_interval(self.range_bundle, row, point_eur=[point]).iloc[0]
        expl = ex.explain_rows(self.val_bundle, row)[0]
        f = fc.forecast_next(self.fc_bundle, row).iloc[0]

        nxt = self.by_player[player_id]
        nxt = nxt[nxt["season"] == season + 1]
        actual_next = num(nxt.iloc[0]["market_value_eur"]) if len(nxt) else None

        warnings = []
        if season < TEST_FROM:
            warnings.append("This season was part of the model's training data, so the valuation is "
                            "in-sample and looks more accurate than it would for a new player.")
        if market >= 100e6:
            warnings.append("Superstar values (above EUR 100M) are compressed by this model: it tends to "
                            "under-predict them and the real value often falls outside the range.")
        if point < 2e6:
            warnings.append("Below EUR 2M the range is least reliable (about 64% coverage instead of 80%).")
        if int(r["minutes"]) < 900:
            warnings.append("Under 900 minutes played: the range is less reliable for low-minute players.")

        return {
            "player_id": player_id, "season": season, "age": num(r["age"], 1), "value_date": text(r["value_date"]),
            "market_value_eur": market, "model_value_eur": round(point),
            "low_eur": round(float(iv.low_eur)), "high_eur": round(float(iv.high_eur)),
            "gap_pct": num((point / market - 1) * 100, 1),
            "market_within_range": bool(iv.low_eur <= market <= iv.high_eur),
            "in_sample": season < TEST_FROM,
            "baseline_value_eur": expl["baseline_value_eur"],
            "factors": expl["factors"],
            "forecast": {
                "for_season": season + 1, "forecast_eur": round(float(f.forecast_eur)),
                "low_eur": round(float(f.low_eur)), "high_eur": round(float(f.high_eur)),
                "expected_change_pct": num(f.expected_change_pct, 1), "actual_value_eur": actual_next,
            },
            "warnings": warnings,
        }

    def model_history(self, player_id: int) -> list[dict]:
        """Model value + 80% range for every season of a player, next to the market value then.
        Seasons before TEST_FROM were in the training data (in_sample=True)."""
        g = self.by_player[player_id]
        pt = tt.predict_values(self.val_bundle, g)
        iv = un.predict_interval(self.range_bundle, g, point_eur=pt)
        out = []
        for i, r in enumerate(g.itertuples()):
            out.append({"season": int(r.season), "date": text(r.value_date), "market_value_eur": num(r.market_value_eur),
                        "model_value_eur": round(float(pt[i])), "low_eur": round(float(iv["low_eur"].iloc[i])),
                        "high_eur": round(float(iv["high_eur"].iloc[i])), "in_sample": int(r.season) < TEST_FROM})
        return out

    # ------------------------------------------------------------------ rankings
    def season_frame(self, season: int) -> pd.DataFrame:
        """All player-seasons of one season with model value, range and forecast. Cached."""
        with self._lock:
            return self._season_frame(season)

    def _season_frame(self, season: int) -> pd.DataFrame:
        if season not in self._frames:
            rows = self.p[self.p["season"] == season]
            if rows.empty:
                raise KeyError(f"no data for season {season}")
            pt = tt.predict_values(self.val_bundle, rows)
            iv = un.predict_interval(self.range_bundle, rows, point_eur=pt)
            f = fc.forecast_next(self.fc_bundle, rows)
            df = rows.assign(model_value_eur=pt, low_eur=iv["low_eur"].to_numpy(), high_eur=iv["high_eur"].to_numpy(),
                             forecast_eur=f["forecast_eur"].to_numpy(),
                             forecast_change_pct=f["expected_change_pct"].to_numpy())
            df["gap_pct"] = (df["model_value_eur"] / df["market_value_eur"] - 1) * 100
            self._frames[season] = df
        return self._frames[season]

    def rankings(self, sort: str = "value", season: int | None = None, position: str | None = None,
                 league: str | None = None, min_age: float | None = None, max_age: float | None = None,
                 min_minutes: int | None = None, min_value: float | None = None,
                 max_value: float | None = None, limit: int = 25) -> dict:
        col, desc, label, wants_minutes = SORTS[sort]
        season = self.max_season if season is None else season
        df = self.season_frame(season)
        if position:
            df = df[df["position"] == position]
        if league:
            df = df[df["league"] == league]
        if min_age is not None:
            df = df[df["age"] >= min_age]
        if max_age is not None:
            df = df[df["age"] <= max_age]
        if sort == "young":
            df = df[df["age"] < 21]
        floor = min_minutes if min_minutes is not None else (900 if wants_minutes else 0)
        df = df[df["minutes"] >= floor]
        band_lo, band_hi = VALUE_BANDS.get(sort, (None, None))
        lo_val = min_value if min_value is not None else band_lo
        hi_val = max_value if max_value is not None else band_hi
        if lo_val is not None:
            df = df[df["market_value_eur"] >= lo_val]
        if hi_val is not None:
            df = df[df["market_value_eur"] <= hi_val]
        df = df[df[col].notna()]

        sign = 1 if desc else -1
        records = df.to_dict("records")
        best = top_k(records, limit, key=lambda r: sign * r[col])           # heap, O(n log k)
        rows = [{
            "rank": i + 1, "player_id": int(r["player_id"]), "name": str(r["name"]),
            "position_code": str(r["position"]), "position": POSITION_LABEL.get(r["position"], str(r["position"])),
            "sub_position": text(r["sub_position"]), "league": str(r["league"]), "club_id": int(r["club_id"]),
            "club_name": self.club_name(r["club_id"]), "age": num(r["age"], 1), "minutes": int(r["minutes"]),
            "goals": int(r["goals"]), "assists": int(r["assists"]),
            "goals_per90": num(r["goals_per90"], 2), "assists_per90": num(r["assists_per90"], 2),
            "market_value_eur": num(r["market_value_eur"]), "model_value_eur": round(r["model_value_eur"]),
            "low_eur": round(r["low_eur"]), "high_eur": round(r["high_eur"]), "gap_pct": num(r["gap_pct"], 1),
            "forecast_eur": round(r["forecast_eur"]), "forecast_change_pct": num(r["forecast_change_pct"], 1),
            "outside_range": ("below" if r["market_value_eur"] < r["low_eur"]
                              else "above" if r["market_value_eur"] > r["high_eur"] else None),
        } for i, r in enumerate(best)]
        return {"sort": sort, "label": label, "season": season, "total_matching": int(len(df)),
                "min_minutes": floor, "min_value_eur": lo_val, "max_value_eur": hi_val, "rows": rows}

    # ------------------------------------------------------------------ similar
    def _engine(self, scope: str) -> SimilarityEngine:
        with self._lock:
            return self._engine_unlocked(scope)

    def _engine_unlocked(self, scope: str) -> SimilarityEngine:
        if scope not in self._engines:
            if scope == "active":
                rows = self.latest[(self.latest["season"] == self.max_season) & (self.latest["minutes"] >= 450)]
            else:   # every player, represented by his most recent season with at least 450 minutes
                played = self.p[self.p["minutes"] >= 450].sort_values(["player_id", "season"])
                rows = played.groupby("player_id").tail(1).set_index("player_id")
            feats = rows[["age", "goals_per90", "assists_per90", "minutes", "appearances",
                          "yellow_cards_per90", "height_in_cm"]].copy()
            feats["height_in_cm"] = feats["height_in_cm"].fillna(feats["height_in_cm"].median())
            feats["minutes"] = feats["minutes"] / 1000
            self._engines[scope] = SimilarityEngine(
                rows.index.astype(int).tolist(), rows["sub_position"].fillna("unknown").tolist(), feats.to_numpy(float))
        return self._engines[scope]

    def similar(self, player_id: int, k: int = 6, scope: str = "active") -> list[dict]:
        engine = self._engine(scope)
        try:
            found = engine.top_k(player_id, k)
        except KeyError:
            return []
        out = []
        for pid, dist in found:
            # display score only: Gaussian kernel over the 7 standardised features, 100 = identical profile
            out.append({**self.card(pid), "distance": round(dist, 3), "match_pct": round(100 * math.exp(-dist ** 2 / 14))})
        return out

    def in_similarity_pool(self, player_id: int, scope: str = "active") -> bool:
        return player_id in self._engine(scope)._row

    # --------------------------------------------------------------- connections
    def teammates(self, player_id: int, season: int | None = None, limit: int = 12) -> dict:
        ids = self.football_graph.teammates(player_id, season)
        best = top_k(ids, limit, key=lambda pid: self.latest.loc[pid, "market_value_eur"] if pid in self.latest.index else 0)
        return {"total": len(ids), "players": [self.card(pid) for pid in best]}

    def connection(self, a: int, b: int) -> dict:
        path = self.football_graph.graph.shortest_path(("player", a), ("player", b))
        if path is None:
            return {"separation": None, "path": []}
        steps = []
        for node in path:
            if node[0] == "player":
                steps.append({"type": "player", **self.card(node[1])})
            else:
                steps.append({"type": "club", "club_id": node[1], "club_name": self.club_name(node[1]), "season": node[2]})
        return {"separation": (len(path) - 1) // 2, "path": steps}

    # ---------------------------------------------------------------- model info
    def global_importance(self) -> list[dict]:
        with self._lock:
            return self._global_importance()

    def _global_importance(self) -> list[dict]:
        if self._global is None:
            test = self.p[self.p["season"] >= TEST_FROM]
            test = test.sample(min(len(test), 2500), random_state=0)       # a sample is plenty and keeps this fast
            imp = ex.global_importance(self.val_bundle, test)
            self._global = [{"concept": c, "avg_effect_pct": float(v)} for c, v in imp["avg_effect_%"].items()]
        return self._global

    def model_info(self) -> dict:
        _, _, _, vmeta = self.val_bundle
        qmeta, fmeta = self.range_bundle[-1], self.fc_bundle[-1]
        return {
            "valuation": vmeta["metrics"], "range": qmeta["metrics"], "forecast": fmeta["metrics"],
            "trained_before_season": vmeta["trained_before_season"],
            "data": {"players": len(self.by_player), "player_seasons": int(len(self.p)),
                     "first_season": int(self.p["season"].min()), "last_season": self.max_season,
                     "leagues": LEAGUE_LABEL},
            "global_importance": self.global_importance(),
        }

    def overview(self) -> dict:
        """Market snapshot of the latest season, where the model is most reliable
        (EUR 2M-100M, 900+ minutes): how many players the market values below / inside / above the model range."""
        df = self.season_frame(self.max_season)
        df = df[(df["minutes"] >= 900) & df["market_value_eur"].between(2e6, 100e6)]
        below = int((df["market_value_eur"] < df["low_eur"]).sum())
        above = int((df["market_value_eur"] > df["high_eur"]).sum())
        return {"season": self.max_season, "players_assessed": int(len(df)), "below_range": below, "above_range": above,
                "inside_range": int(len(df)) - below - above, "median_gap_pct": num(df["gap_pct"].median(), 1),
                "total_market_value_eur": num(self.season_frame(self.max_season)["market_value_eur"].sum())}

    def meta(self) -> dict:
        return {"players": len(self.by_player), "player_seasons": int(len(self.p)), "overview": self.overview(),
                "typical_error_pct": num(self.val_bundle[-1]["metrics"].get("median_APE_%"), 0),
                "max_season": self.max_season, "first_season": int(self.p["season"].min()),
                "test_from_season": TEST_FROM, "leagues": LEAGUE_LABEL, "positions": POSITION_LABEL,
                "rankings": [{"id": k, "label": v[2]} for k, v in SORTS.items()],
                "has_club_names": bool(self.clubs)}
