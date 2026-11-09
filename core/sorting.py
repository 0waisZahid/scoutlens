"""Merge sort written from scratch.

Divide the list in half, sort each half recursively, then merge the two sorted
halves. The list is halved log2(n) times and every level does O(n) merging work,
so the total is O(n log n) in the best, average and worst case.

It is stable: items with equal keys keep their original order. That matters for
rankings, e.g. players with the same value stay in alphabetical order if the
list was alphabetical before.

Extra memory: O(n) for the merged lists.
"""
from __future__ import annotations

from typing import Any, Callable


def merge_sort(items, key: Callable[[Any], Any] = lambda x: x, reverse: bool = False) -> list:
    """Return a NEW sorted list; the input is not modified."""
    items = list(items)
    if len(items) <= 1:
        return items
    mid = len(items) // 2
    left = merge_sort(items[:mid], key, reverse)
    right = merge_sort(items[mid:], key, reverse)
    return _merge(left, right, key, reverse)


def _merge(left: list, right: list, key, reverse: bool) -> list:
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        kl, kr = key(left[i]), key(right[j])
        # "<=" / ">=" take from the LEFT on ties, which makes the sort stable
        take_left = kl >= kr if reverse else kl <= kr
        if take_left:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out
