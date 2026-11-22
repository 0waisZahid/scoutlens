import random

import numpy as np
import pytest
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, shortest_path

from core.graph import FootballGraph, Graph


def random_graph(n=200, m=260, seed=0):
    rng = random.Random(seed)
    g = Graph()
    for i in range(n):
        g.add_node(i)
    for _ in range(m):
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            g.add_edge(u, v)
    return g


def to_scipy(g, n):
    rows, cols = [], []
    for u in g.nodes():
        for v in g.neighbors(u):
            rows.append(u)
            cols.append(v)
    return csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))


def test_edges_are_undirected_and_not_duplicated():
    g = Graph()
    g.add_edge("a", "b")
    g.add_edge("b", "a")                      # same edge again
    assert g.neighbors("a") == ["b"] and g.neighbors("b") == ["a"]
    assert len(g) == 2 and g.edge_count == 1


def test_self_loop_and_unknown_node_rejected():
    g = Graph()
    with pytest.raises(ValueError):
        g.add_edge(1, 1)
    with pytest.raises(KeyError):
        g.neighbors(99)
    with pytest.raises(KeyError):
        g.bfs_distances(99)


def test_bfs_visits_level_by_level():
    g = Graph()
    for u, v in [(1, 2), (1, 3), (2, 4), (3, 5), (4, 6)]:
        g.add_edge(u, v)
    assert g.bfs(1) == [1, 2, 3, 4, 5, 6]
    assert g.bfs_distances(1) == {1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3}


def test_max_depth_limits_the_search():
    g = Graph()
    for u, v in [(1, 2), (2, 3), (3, 4)]:
        g.add_edge(u, v)
    assert g.bfs_distances(1, max_depth=2) == {1: 0, 2: 1, 3: 2}


def test_bfs_distances_match_scipy():
    g = random_graph()
    ref = shortest_path(to_scipy(g, 200), method="D", directed=False, unweighted=True, indices=0)
    ours = g.bfs_distances(0)
    for node in range(200):
        if np.isinf(ref[node]):
            assert node not in ours
        else:
            assert ours[node] == ref[node]


def test_shortest_path_is_valid_and_shortest():
    g = random_graph()
    dist = g.bfs_distances(0)
    for target in list(dist)[:60]:
        path = g.shortest_path(0, target)
        assert path[0] == 0 and path[-1] == target
        assert len(path) - 1 == dist[target]
        assert all(b in g.neighbors(a) for a, b in zip(path, path[1:]))


def test_shortest_path_edge_cases():
    g = Graph()
    g.add_edge(1, 2)
    g.add_node(3)                              # isolated
    assert g.shortest_path(1, 1) == [1]
    assert g.shortest_path(1, 3) is None
    with pytest.raises(KeyError):
        g.shortest_path(1, 99)


def test_connected_components_match_scipy():
    g = random_graph(n=200, m=150, seed=5)     # sparse, so several components
    n_ref, labels = connected_components(to_scipy(g, 200), directed=False)
    ref = {frozenset(np.where(labels == k)[0].tolist()) for k in range(n_ref)}
    ours = {frozenset(c) for c in g.connected_components()}
    assert ours == ref
    sizes = [len(c) for c in g.connected_components()]
    assert sizes == sorted(sizes, reverse=True)


def sample_football_graph():
    return FootballGraph.from_rows([
        (1, "A", 2020), (2, "A", 2020),        # 1 and 2 were teammates in 2020
        (2, "A", 2021), (3, "A", 2021),        # 2 and 3 in 2021
        (3, "B", 2022), (5, "B", 2022),        # 3 and 5 in 2022
        (4, "B", 2020),                        # 4 never shared a club-season with anyone
    ])


def test_teammates_by_season_and_overall():
    fg = sample_football_graph()
    assert fg.teammates(1, season=2020) == [2]
    assert fg.teammates(1, season=2021) == []
    assert fg.teammates(2) == [1, 3]
    assert fg.teammates(4) == []


def test_separation_counts_teammate_hops():
    fg = sample_football_graph()
    assert fg.separation(1, 1) == 0
    assert fg.separation(1, 2) == 1
    assert fg.separation(1, 3) == 2
    assert fg.separation(1, 5) == 3
    assert fg.separation(1, 4) is None


def test_unknown_player_raises():
    fg = sample_football_graph()
    with pytest.raises(KeyError):
        fg.teammates(999)
    with pytest.raises(KeyError):
        fg.separation(1, 999)


def test_teammates_is_symmetric_on_random_data():
    rng = random.Random(9)
    rows = [(rng.randrange(60), rng.randrange(6), rng.randrange(2018, 2024)) for _ in range(300)]
    fg = FootballGraph.from_rows(rows)
    for a in {r[0] for r in rows}:
        for b in fg.teammates(a):
            assert a in fg.teammates(b)
            assert a != b
