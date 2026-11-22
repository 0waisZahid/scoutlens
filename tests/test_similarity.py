import numpy as np
import pytest
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from core.similarity import SimilarityEngine


def make_data(n=300, d=6, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, d)) * rng.uniform(0.5, 50, size=d)     # very different scales
    ids = list(range(1000, 1000 + n))
    pos = list(rng.choice(["GK", "DF", "MF", "FW"], size=n))
    return ids, pos, X


def sklearn_neighbours(ids, pos, X, query_id, k, metric):
    """Reference answer: standardise, restrict to the same position, ask scikit-learn."""
    Z = StandardScaler().fit_transform(X)
    q = ids.index(query_id)
    rows = [i for i in range(len(ids)) if pos[i] == pos[q] and i != q]
    nn = NearestNeighbors(n_neighbors=k, metric=metric, algorithm="brute").fit(Z[rows])
    dist, idx = nn.kneighbors(Z[[q]])
    return [ids[rows[i]] for i in idx[0]], dist[0]


@pytest.mark.parametrize("metric", ["euclidean", "cosine"])
def test_matches_scikit_learn(metric):
    ids, pos, X = make_data()
    engine = SimilarityEngine(ids, pos, X, metric=metric)
    for query in (ids[0], ids[57], ids[200]):
        ours = engine.top_k(query, k=8)
        ref_ids, ref_dist = sklearn_neighbours(ids, pos, X, query, 8, metric)
        assert [p for p, _ in ours] == ref_ids
        assert [d for _, d in ours] == pytest.approx(list(ref_dist), abs=1e-9)


def test_results_exclude_self_and_stay_in_position_group():
    ids, pos, X = make_data()
    engine = SimilarityEngine(ids, pos, X)
    query = ids[10]
    result = engine.top_k(query, k=20)
    got = [p for p, _ in result]
    assert query not in got
    assert all(pos[ids.index(p)] == pos[10] for p in got)


def test_results_sorted_nearest_first():
    ids, pos, X = make_data()
    dists = [d for _, d in SimilarityEngine(ids, pos, X).top_k(ids[3], k=15)]
    assert dists == sorted(dists)


def test_same_position_false_searches_everyone():
    ids = [1, 2, 3]
    pos = ["GK", "FW", "FW"]
    X = [[0.0, 0.0], [0.1, 0.1], [5.0, 5.0]]
    engine = SimilarityEngine(ids, pos, X)
    assert [p for p, _ in engine.top_k(1, k=2, same_position=True)] == []
    assert [p for p, _ in engine.top_k(1, k=2, same_position=False)] == [2, 3]


def test_k_larger_than_group_returns_whole_group():
    ids, pos, X = make_data(n=40)
    engine = SimilarityEngine(ids, pos, X)
    group = [i for i in range(40) if pos[i] == pos[0]]
    assert len(engine.top_k(ids[0], k=1000)) == len(group) - 1


def test_identical_player_is_nearest():
    ids = [1, 2, 3, 4]
    pos = ["FW"] * 4
    X = [[1.0, 2.0], [9.0, 9.0], [1.0, 2.0], [5.0, 1.0]]
    best_id, best_dist = SimilarityEngine(ids, pos, X).top_k(1, k=1)[0]
    assert best_id == 3 and best_dist == pytest.approx(0.0)


def test_constant_feature_does_not_crash():
    ids = [1, 2, 3]
    pos = ["FW"] * 3
    X = [[1.0, 7.0], [2.0, 7.0], [3.0, 7.0]]        # second column never changes
    assert len(SimilarityEngine(ids, pos, X).top_k(1, k=2)) == 2


def test_input_validation():
    with pytest.raises(ValueError):
        SimilarityEngine([1, 2], ["FW"], [[1.0], [2.0]])
    with pytest.raises(ValueError):
        SimilarityEngine([1], ["FW"], [[1.0]], metric="manhattan")
    with pytest.raises(KeyError):
        SimilarityEngine([1], ["FW"], [[1.0]]).top_k(99)
