"""Measured running time of merge sort vs Python's sorted(), against theory.

    python -m benchmarks.bench_sort

If merge sort is O(n log n), the last column (time / (n * log2 n)) stays roughly
constant as n grows, and doubling n multiplies the time by a bit more than 2.
"""
import math
import random
import time

from core.sorting import merge_sort

SIZES = [1_000, 2_000, 4_000, 8_000, 16_000, 32_000, 64_000, 128_000]
REPEATS = 3


def best_time(fn, data) -> float:
    best = float("inf")
    for _ in range(REPEATS):
        start = time.perf_counter()
        fn(data)
        best = min(best, time.perf_counter() - start)
    return best


if __name__ == "__main__":
    random.seed(0)
    print(f"{'n':>8} {'merge_sort (s)':>15} {'sorted (s)':>11} {'x2 growth':>10} {'ns per n*log2(n)':>17}")
    prev = None
    for n in SIZES:
        data = [random.random() for _ in range(n)]
        t_merge = best_time(merge_sort, data)
        t_py = best_time(sorted, data)
        growth = f"{t_merge / prev:.2f}" if prev else "-"
        per_unit = t_merge / (n * math.log2(n)) * 1e9
        print(f"{n:>8} {t_merge:>15.4f} {t_py:>11.4f} {growth:>10} {per_unit:>17.1f}")
        prev = t_merge
    print("\nTheory: doubling n should multiply the time by about 2.1 (n log n),")
    print("and the last column should stay roughly constant.")
