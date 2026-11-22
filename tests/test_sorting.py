import random

from core.sorting import merge_sort


def test_sorts_small_list():
    assert merge_sort([5, 2, 9, 1, 5, 6]) == [1, 2, 5, 5, 6, 9]


def test_empty_and_single():
    assert merge_sort([]) == []
    assert merge_sort([7]) == [7]


def test_already_sorted_and_reversed():
    assert merge_sort([1, 2, 3, 4]) == [1, 2, 3, 4]
    assert merge_sort([4, 3, 2, 1]) == [1, 2, 3, 4]


def test_does_not_modify_input():
    data = [3, 1, 2]
    merge_sort(data)
    assert data == [3, 1, 2]


def test_reverse_order():
    assert merge_sort([3, 1, 2], reverse=True) == [3, 2, 1]


def test_key_function():
    players = [("A", 30), ("B", 10), ("C", 20)]
    assert merge_sort(players, key=lambda p: p[1]) == [("B", 10), ("C", 20), ("A", 30)]


def test_stable_for_equal_keys():
    items = [("a", 1), ("b", 1), ("c", 0), ("d", 1), ("e", 0)]
    assert merge_sort(items, key=lambda x: x[1]) == [("c", 0), ("e", 0), ("a", 1), ("b", 1), ("d", 1)]
    # also stable in reverse order, like Python's sorted(..., reverse=True)
    assert merge_sort(items, key=lambda x: x[1], reverse=True) == \
        sorted(items, key=lambda x: x[1], reverse=True)


def test_matches_sorted_on_random_data():
    random.seed(4)
    for size in (2, 10, 100, 1000):
        data = [random.randint(0, 50) for _ in range(size)]      # many duplicates
        assert merge_sort(data) == sorted(data)
        assert merge_sort(data, reverse=True) == sorted(data, reverse=True)


def test_matches_sorted_with_key_on_random_data():
    random.seed(5)
    data = [(i, random.randint(0, 20)) for i in range(500)]
    assert merge_sort(data, key=lambda x: x[1]) == sorted(data, key=lambda x: x[1])
