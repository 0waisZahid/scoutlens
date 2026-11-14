"""Similar-player search.

How it works
1. Each player is a vector of numeric features (age, per-90 stats, ...).
2. Every feature is standardised to a z-score, so that minutes (thousands) do not
   drown out goals per 90 (fractions): z = (x - mean) / std.
3. A position index (an inverted index: position -> rows) limits the search to
   players in the same position group, so a striker is never matched to a goalkeeper.
4. Distance to every candidate is computed (Euclidean or cosine) and the k nearest
   are kept with the min-heap from core.heap.

Cost per query: O(m*d + m log k), where m = players in the position group and
d = number of features. No sorting of all candidates is needed.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from core.heap import top_k

METRICS = ("euclidean", "cosine")


class SimilarityEngine:
    def __init__(self, player_ids, positions, features, metric: str = "euclidean") -> None:
        if metric not in METRICS:
            raise ValueError(f"metric must be one of {METRICS}")
        X = np.asarray(features, dtype=float)
        if X.ndim != 2:
            raise ValueError("features must be a 2-D table (players x features)")
        if not (len(player_ids) == len(positions) == len(X)):
            raise ValueError("player_ids, positions and features must have the same length")

        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std[std == 0] = 1.0                      # constant column: avoid dividing by zero
        self._z = ((X - mean) / std).tolist()    # standardised vectors, one list per player

        self._ids = list(player_ids)
        self._positions = list(positions)
        self._row = {pid: i for i, pid in enumerate(self._ids)}
        self._by_position: dict = defaultdict(list)          # position index
        for i, pos in enumerate(self._positions):
            self._by_position[pos].append(i)
        self.metric = metric

    def _distance(self, a: list[float], b: list[float]) -> float:
        if self.metric == "euclidean":
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 1.0                           # cosine undefined for a zero vector
        return 1.0 - dot / (na * nb)

    def top_k(self, player_id, k: int = 5, same_position: bool = True) -> list[tuple]:
        """Return up to k (player_id, distance) pairs, most similar first."""
        if player_id not in self._row:
            raise KeyError(f"unknown player_id: {player_id}")
        row = self._row[player_id]
        pool = self._by_position[self._positions[row]] if same_position else range(len(self._ids))
        query = self._z[row]
        scored = [(self._distance(query, self._z[j]), j) for j in pool if j != row]
        best = top_k(scored, k, key=lambda t: -t[0])         # largest -distance = nearest
        return [(self._ids[j], d) for d, j in best]
