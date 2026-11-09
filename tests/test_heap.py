import random

import pytest

from core.heap import MinHeap, top_k


def is_valid_heap(h: MinHeap) -> bool:
    a, key = h._a, h._key
    return all(key(a[(i - 1) // 2]) <= key(a[i]) for i in range(1, len(a)))


def test_pop_returns_items_in_ascending_order():
    h = MinHeap()
    for x in [5, 3, 8, 1, 9, 2]:
        h.push(x)
    assert [h.pop() for _ in range(len(h))] == [1, 2, 3, 5, 8, 9]


def test_peek_does_not_remove():
    h = MinHeap()
    h.push(4)
    h.push(2)
    assert h.peek() == 2
    assert len(h) == 2


def test_empty_heap_raises():
    with pytest.raises(IndexError):
        MinHeap().pop()
    with pytest.raises(IndexError):
        MinHeap().peek()


def test_key_function_orders_by_key():
    h = MinHeap(key=lambda p: p[1])
    for item in [("a", 30), ("b", 10), ("c", 20)]:
        h.push(item)
    assert h.pop() == ("b", 10)


def test_heap_property_holds_after_many_operations():
    random.seed(1)
    h = MinHeap()
    for _ in range(500):
        h.push(random.randint(0, 1000))
        assert is_valid_heap(h)
    for _ in range(250):
        h.pop()
        assert is_valid_heap(h)


def test_matches_sorted_on_random_data():
    random.seed(2)
    data = [random.randint(0, 10_000) for _ in range(1000)]
    h = MinHeap()
    for x in data:
        h.push(x)
    assert [h.pop() for _ in range(len(h))] == sorted(data)


def test_top_k_matches_sorted_reference():
    random.seed(3)
    data = random.sample(range(100_000), 2000)          # unique values
    assert top_k(data, 10) == sorted(data, reverse=True)[:10]


def test_top_k_with_key():
    players = [{"name": "A", "v": 5}, {"name": "B", "v": 50}, {"name": "C", "v": 20}, {"name": "D", "v": 35}]
    best = top_k(players, 2, key=lambda p: p["v"])
    assert [p["name"] for p in best] == ["B", "D"]


def test_top_k_edge_cases():
    assert top_k([3, 1, 2], 0) == []
    assert top_k([3, 1, 2], -5) == []
    assert top_k([3, 1, 2], 10) == [3, 2, 1]             # k larger than the list
    assert top_k([], 3) == []


def test_top_k_does_not_modify_input():
    data = [4, 9, 1, 7]
    top_k(data, 2)
    assert data == [4, 9, 1, 7]
