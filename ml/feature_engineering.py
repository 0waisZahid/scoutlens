"""Phase 2 feature engineering (leakage-safe).

Everything here uses only information that exists BEFORE the player's value is
set (his own current-season stats, plus anything from earlier seasons). No
feature looks at any player's market value from the season being predicted.
tests/test_phase2.py enforces that rule.

Feature groups (added cumulatively in the ablation in ml/train_and_tune.py):

  base           age, minutes, goals/assists per 90, position, league
  extra          appearances, cards, height, sub-position, foot
  club           club strength from the PREVIOUS season (no same-season leakage)
  history        last season's output, 2-season rates, recent minutes,
                 club tenure (contract proxy), transfer / club-move signals
  context        share of club minutes and goal involvements, goals/assists
                 relative to peers in the same position and season
  nationality    top-N countries
  value_history  the player's own last known value (forecast mode: this is an
                 anchor, not a from-scratch estimate, so it is kept separate)

Not possible with the current data (see README): contract years left, national
team caps, xG/passing/tackles. Drop them in via ml/train_and_tune.py's
`--extra` file when you have them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.leakage_check import club_mean

TARGET = "market_value_eur"
GROUP_ORDER = ["base", "extra", "club", "history", "context", "nationality", "value_history"]
POSITIONS = ["DF", "FW", "GK", "MF"]


def _prev_season_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Each row's own stats from season-1 (NaN if he has no row for season-1)."""
    prev = df[["player_id", "season", "club_id", "minutes", "goals", "assists"]].copy()
    prev["season"] = prev["season"] + 1
    prev = prev.rename(columns={"club_id": "prev_club_id", "minutes": "prev_minutes",
                                "goals": "prev_goals", "assists": "prev_assists"})
    out = df[["player_id", "season"]].merge(prev, on=["player_id", "season"], how="left")
    out.index = df.index
    return out.drop(columns=["player_id", "season"])


def _recent_minutes(df: pd.DataFrame, years: int = 3) -> pd.Series:
    """Total minutes over the previous `years` seasons (a window, so it does not
    drift upward over time the way 'career minutes since 2012' would)."""
    total = pd.Series(0.0, index=df.index)
    for lag in range(1, years + 1):
        m = df[["player_id", "season", "minutes"]].copy()
        m["season"] = m["season"] + lag
        m = df[["player_id", "season"]].merge(m, on=["player_id", "season"], how="left")
        total += m["minutes"].fillna(0).values
    return total


def _tenure(df: pd.DataFrame) -> pd.Series:
    """Consecutive previous seasons at the SAME club (0 = new signing / first seen)."""
    d = df[["player_id", "season", "club_id"]].sort_values(["player_id", "season"])
    ps = d.groupby("player_id")["season"].shift()
    pc = d.groupby("player_id")["club_id"].shift()
    cont = (ps == d["season"] - 1) & (pc == d["club_id"])
    run = (~cont).groupby(d["player_id"]).cumsum()
    ten = d.groupby([d["player_id"], run]).cumcount()
    return ten.reindex(df.index)


def _safe_div(a, b):
    return np.where(b > 0, a / np.where(b > 0, b, 1), 0.0)


def _peer_z(df: pd.DataFrame, col: str, min_minutes: int = 450) -> pd.Series:
    """z-score of a per-90 stat versus peers of the same position in the same season."""
    ok = df[df["minutes"] >= min_minutes]
    g = ok.groupby(["position", "season"])[col]
    stats = pd.DataFrame({"mu": g.mean(), "sd": g.std()}).reset_index()
    m = df[["position", "season"]].merge(stats, on=["position", "season"], how="left")
    sd = m["sd"].replace(0, np.nan).values
    return pd.Series((df[col].values - m["mu"].values) / sd, index=df.index).fillna(0.0)


def _prev_known_value(df: pd.DataFrame, mv: pd.DataFrame) -> pd.DataFrame:
    """Player's last valuation dated strictly before 1 Aug of the season (max 2 years old)."""
    vals = mv.rename(columns={"date": "vdate"}).copy()
    vals["vdate"] = pd.to_datetime(vals["vdate"])
    vals = vals.sort_values("vdate")
    left = df[["player_id", "season"]].copy()
    left["row"] = np.arange(len(left))
    left["cut"] = pd.to_datetime(left["season"].astype(str) + "-08-01")
    left = left.sort_values("cut")
    m = pd.merge_asof(left, vals, left_on="cut", right_on="vdate", by="player_id",
                      direction="backward", allow_exact_matches=False,
                      tolerance=pd.Timedelta(days=730))
    m = m.sort_values("row")
    out = pd.DataFrame({
        "prev_value": m["value_eur"].values,
        "prev_value_age_months": ((m["cut"] - m["vdate"]).dt.days / 30.4).values,
    }, index=df.index)
    return out


def prepare(df: pd.DataFrame, mv: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add all engineered, past-only columns. Does not depend on the train/test split."""
    out = df.copy()
    out = out.join(_prev_season_cols(df))

    out["prev_goals_p90"] = np.where(out.prev_minutes > 0, out.prev_goals / out.prev_minutes * 90, np.nan)
    out["prev_assists_p90"] = np.where(out.prev_minutes > 0, out.prev_assists / out.prev_minutes * 90, np.nan)
    pm = out.prev_minutes.fillna(0)
    out["roll_goals_p90"] = _safe_div(out.goals + out.prev_goals.fillna(0), (out.minutes + pm) / 90)
    out["roll_assists_p90"] = _safe_div(out.assists + out.prev_assists.fillna(0), (out.minutes + pm) / 90)
    out["recent_minutes"] = _recent_minutes(df)
    out["tenure"] = _tenure(df)
    out["club_changed"] = (out.prev_club_id.notna() & (out.prev_club_id != out.club_id)).astype(float)
    out["new_signing"] = ((out.tenure == 0) & out.prev_club_id.notna()).astype(float)

    # club strength: mean log value of the club's players in the PREVIOUS season, excluding himself
    out["club_strength_lag"] = club_mean(out, None, out.season - 1, exclude_self=True)
    out["club_rel_league"] = out.club_strength_lag - out.groupby(["league", "season"])["club_strength_lag"].transform("mean")

    # strength of the club he came from (only meaningful for movers)
    old = out.copy()
    old["club_id"] = old["prev_club_id"]
    has_prev = old["club_id"].notna()
    prev_cs = pd.Series(np.nan, index=out.index)
    prev_cs[has_prev] = club_mean(old[has_prev], None, old.loc[has_prev, "season"] - 1, exclude_self=True)
    out["move_delta"] = np.where(out.club_changed == 1, out.club_strength_lag - prev_cs, 0.0)

    tot = out.groupby(["club_id", "season"])[["minutes", "goals", "assists"]].transform("sum")
    out["minutes_share"] = _safe_div(out.minutes, tot.minutes)
    out["ga_share"] = _safe_div(out.goals + out.assists, tot.goals + tot.assists)
    out["goals_z"] = _peer_z(out, "goals_per90")
    out["assists_z"] = _peer_z(out, "assists_per90")

    if mv is not None:
        out = out.join(_prev_known_value(df, mv))
    return out


class FeatureBuilder:
    """Fit on training rows (learns category lists), then transform any rows."""

    def __init__(self, top_countries: int = 15):
        self.top_countries = top_countries

    def fit(self, prepared_train: pd.DataFrame) -> "FeatureBuilder":
        p = prepared_train
        self.leagues_ = sorted(p.league.dropna().unique())
        self.subpos_ = sorted(p.sub_position.fillna("unknown").unique())
        self.foot_ = sorted(p.foot.fillna("unknown").unique())
        self.countries_ = list(p.country_of_citizenship.value_counts().head(self.top_countries).index)
        self.height_median_ = float(p.height_in_cm.median())
        return self

    def transform(self, p: pd.DataFrame, trend, groups=GROUP_ORDER) -> pd.DataFrame:
        a = p.age - 26
        sub = p.sub_position.fillna("unknown")
        foot = p.foot.fillna("unknown")
        off_prev = trend(p.season - 1)
        parts = {}

        base = pd.DataFrame({"age": a, "age_sq": a ** 2, "minutes_k": p.minutes / 1000,
                             "goals_p90": p.goals_per90, "assists_p90": p.assists_per90}, index=p.index)
        for c in POSITIONS:
            base[f"pos_{c}"] = (p.position == c).astype(float)
        for c in self.leagues_:
            base[f"lg_{c}"] = (p.league == c).astype(float)
        parts["base"] = base

        extra = pd.DataFrame({"appearances": p.appearances, "yellow_p90": p.yellow_cards_per90,
                              "red_p90": p.red_cards_per90,
                              "height": p.height_in_cm.fillna(self.height_median_)}, index=p.index)
        for c in self.subpos_:
            extra[f"sub_{c}"] = (sub == c).astype(float)
        for c in self.foot_:
            extra[f"foot_{c}"] = (foot == c).astype(float)
        parts["extra"] = extra

        parts["club"] = pd.DataFrame({"club_strength_lag": p.club_strength_lag - off_prev,
                                      "club_rel_league": p.club_rel_league}, index=p.index)

        parts["history"] = pd.DataFrame({
            "prev_minutes_k": p.prev_minutes / 1000, "prev_goals_p90": p.prev_goals_p90,
            "prev_assists_p90": p.prev_assists_p90, "roll_goals_p90": p.roll_goals_p90,
            "roll_assists_p90": p.roll_assists_p90, "recent_minutes_k": p.recent_minutes / 1000,
            "tenure": p.tenure.clip(upper=4), "club_changed": p.club_changed,
            "new_signing": p.new_signing, "move_delta": p.move_delta}, index=p.index)

        parts["context"] = pd.DataFrame({"minutes_share": p.minutes_share, "ga_share": p.ga_share,
                                         "goals_z": p.goals_z, "assists_z": p.assists_z}, index=p.index)

        nat = pd.DataFrame(index=p.index)
        for c in self.countries_:
            nat[f"nat_{c}"] = (p.country_of_citizenship == c).astype(float)
        parts["nationality"] = nat

        if "prev_value" in p.columns:
            parts["value_history"] = pd.DataFrame({
                "prev_log_value": np.log(p.prev_value) - off_prev,
                "prev_value_age_months": p.prev_value_age_months}, index=p.index)

        keep = [g for g in GROUP_ORDER if g in groups and g in parts]
        return pd.concat([parts[g] for g in keep], axis=1)
