"""Min-heap written from scratch, plus an O(n log k) top-k helper.

A min-heap is a binary tree stored in a list where every parent is <= its
children, so the smallest item is always at index 0.

    push / pop : O(log n)      peek : O(1)

top_k keeps a heap of only the k best items seen so far. For each of the n
items it does at most one O(log k) update, so ranking costs O(n log k),
cheaper than sorting everything (O(n log n)) when k is much smaller than n.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable


class MinHeap:
    def __init__(self, key: Callable[[Any], Any] = lambda x: x) -> None:
        self._a: list[Any] = []
        self._key = key

    def __len__(self) -> int:
        return len(self._a)

    def peek(self) -> Any:
        if not self._a:
            raise IndexError("peek from empty heap")
        return self._a[0]

    def push(self, item: Any) -> None:
        self._a.append(item)
        self._sift_up(len(self._a) - 1)

    def pop(self) -> Any:
        """Remove and return the smallest item."""
        if not self._a:
            raise IndexError("pop from empty heap")
        last = self._a.pop()
        if not self._a:
            return last
        smallest, self._a[0] = self._a[0], last
        self._sift_down(0)
        return smallest

    def replace_root(self, item: Any) -> Any:
        """Pop the smallest item and push `item` in one O(log n) step."""
        if not self._a:
            raise IndexError("replace on empty heap")
        smallest, self._a[0] = self._a[0], item
        self._sift_down(0)
        return smallest

    def _sift_up(self, i: int) -> None:
        a, key = self._a, self._key
        while i > 0:
            parent = (i - 1) // 2
            if key(a[i]) < key(a[parent]):
                a[i], a[parent] = a[parent], a[i]
                i = parent
            else:
                break

    def _sift_down(self, i: int) -> None:
        a, key, n = self._a, self._key, len(self._a)
        while True:
            left, right, smallest = 2 * i + 1, 2 * i + 2, i
            if left < n and key(a[left]) < key(a[smallest]):
                smallest = left
            if right < n and key(a[right]) < key(a[smallest]):
                smallest = right
            if smallest == i:
                return
            a[i], a[smallest] = a[smallest], a[i]
            i = smallest


def top_k(items: Iterable[Any], k: int, key: Callable[[Any], Any] = lambda x: x) -> list[Any]:
    """Return the k items with the LARGEST key, best first. O(n log k)."""
    if k <= 0:
        return []
    heap = MinHeap(key)
    for item in items:
        if len(heap) < k:
            heap.push(item)
        elif key(item) > key(heap.peek()):     # beats the weakest of the current top k
            heap.replace_root(item)
    result = []
    while len(heap):
        result.append(heap.pop())               # smallest first ...
    result.reverse()                            # ... so flip to best first
    return result
