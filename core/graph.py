"""Graph with breadth-first search (BFS), plus a football layer on top.

Graph         undirected graph stored as an adjacency list (node -> list of neighbours).
              BFS visits nodes level by level using a queue, so every operation below is
              O(V + E): V = number of nodes, E = number of edges.

FootballGraph links each player to the "stints" he played in, where a stint is one club
in one season. Two players who share a stint were teammates:

        player 1 --- (Club A, 2020) --- player 2 --- (Club A, 2021) --- player 3

    teammates(1)        -> [2]        same club-season, any season
    teammates(2)        -> [1, 3]
    separation(1, 3)    -> 2          1 -> 2 -> 3, like "six degrees of Kevin Bacon"
"""
from __future__ import annotations

from collections import deque
from typing import Hashable, Iterable


class Graph:
    """Undirected graph. Edge insertion checks for duplicates, which costs O(degree)."""

    def __init__(self) -> None:
        self._adj: dict[Hashable, list[Hashable]] = {}
        self._edges = 0

    def __len__(self) -> int:                    # V
        return len(self._adj)

    def __contains__(self, node: Hashable) -> bool:
        return node in self._adj

    @property
    def edge_count(self) -> int:                 # E
        return self._edges

    def nodes(self) -> list:
        return list(self._adj)

    def add_node(self, node: Hashable) -> None:
        self._adj.setdefault(node, [])

    def add_edge(self, u: Hashable, v: Hashable) -> None:
        if u == v:
            raise ValueError("self-loops are not allowed")
        self.add_node(u)
        self.add_node(v)
        if v not in self._adj[u]:
            self._adj[u].append(v)
            self._adj[v].append(u)
            self._edges += 1

    def neighbors(self, node: Hashable) -> list:
        if node not in self._adj:
            raise KeyError(f"unknown node: {node!r}")
        return list(self._adj[node])

    def bfs_distances(self, start: Hashable, max_depth: int | None = None) -> dict:
        """Distance (number of edges) from start to every reachable node. O(V + E).

        Nodes are stored in the order they are discovered, which is the BFS visit order.
        With max_depth, nodes further away than that are not explored.
        """
        if start not in self._adj:
            raise KeyError(f"unknown node: {start!r}")
        dist = {start: 0}
        queue = deque([start])
        while queue:
            u = queue.popleft()
            if max_depth is not None and dist[u] >= max_depth:
                continue
            for v in self._adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        return dist

    def bfs(self, start: Hashable) -> list:
        """Nodes in breadth-first visit order."""
        return list(self.bfs_distances(start))

    def shortest_path(self, src: Hashable, dst: Hashable) -> list | None:
        """Fewest-edges path from src to dst, or None if they are not connected."""
        for n in (src, dst):
            if n not in self._adj:
                raise KeyError(f"unknown node: {n!r}")
        if src == dst:
            return [src]
        parent = {src: None}
        queue = deque([src])
        while queue:
            u = queue.popleft()
            for v in self._adj[u]:
                if v not in parent:
                    parent[v] = u
                    if v == dst:
                        path = [v]
                        while path[-1] != src:
                            path.append(parent[path[-1]])
                        return path[::-1]
                    queue.append(v)
        return None

    def connected_components(self) -> list[set]:
        """Groups of nodes that can reach each other, largest first. O(V + E)."""
        seen: set = set()
        comps: list[set] = []
        for node in self._adj:
            if node not in seen:
                comp = set(self.bfs_distances(node))
                seen |= comp
                comps.append(comp)
        comps.sort(key=len, reverse=True)
        return comps


class FootballGraph:
    """Players linked to the club-seasons ("stints") they played in."""

    def __init__(self) -> None:
        self._g = Graph()

    @staticmethod
    def _player(player_id) -> tuple:
        return ("player", player_id)

    @staticmethod
    def _stint(club_id, season) -> tuple:
        return ("stint", club_id, season)

    @property
    def graph(self) -> Graph:
        return self._g

    @classmethod
    def from_rows(cls, rows: Iterable[tuple]) -> "FootballGraph":
        """Build from (player_id, club_id, season) tuples."""
        fg = cls()
        for player_id, club_id, season in rows:
            fg.add_stint(player_id, club_id, season)
        return fg

    def add_stint(self, player_id, club_id, season) -> None:
        self._g.add_edge(self._player(player_id), self._stint(club_id, season))

    def has_player(self, player_id) -> bool:
        return self._player(player_id) in self._g

    def teammates(self, player_id, season=None) -> list:
        """Sorted ids of players who shared a club-season with this player.

        With season=None every season counts (BFS to depth 2: player -> stint -> player).
        """
        node = self._player(player_id)
        if node not in self._g:
            raise KeyError(f"unknown player_id: {player_id}")
        if season is None:
            dist = self._g.bfs_distances(node, max_depth=2)
            found = [n for n, d in dist.items() if d == 2]
        else:
            found = []
            for stint in self._g.neighbors(node):
                if stint[2] == season:
                    found.extend(self._g.neighbors(stint))
        return sorted({n[1] for n in found if n != node})

    def separation(self, a, b) -> int | None:
        """Teammate hops between two players (0 = same player), None if not connected."""
        path = self._g.shortest_path(self._player(a), self._player(b))
        return None if path is None else (len(path) - 1) // 2
