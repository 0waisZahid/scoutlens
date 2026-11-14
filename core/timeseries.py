"""Time-series routines written from scratch.

Used to describe how a player changes over time (recent form, value trend).

    moving_average        sliding window, O(n)   (one pass, running sum)
    exponential_smoothing recent form, O(n)      (recent values count more)
    linear_trend          least-squares slope, O(n)   (closed-form, no iteration)

All three accept plain Python lists (or any sequence of numbers).
"""
from __future__ import annotations

import math
from typing import Sequence


def moving_average(values: Sequence[float], window: int) -> list[float]:
    """Trailing moving average, same length as the input.

    The first window-1 positions have no full window yet and are NaN (the same
    convention as pandas rolling(window).mean()).

    A running sum is updated each step (add the new value, subtract the one that
    left the window), so the whole series costs O(n), not O(n * window).
    """
    if window < 1:
        raise ValueError("window must be at least 1")
    n = len(values)
    out = [math.nan] * n
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= window:
            running -= values[i - window]
        if i >= window - 1:
            out[i] = running / window
    return out


def exponential_smoothing(values: Sequence[float], alpha: float) -> list[float]:
    """Exponentially weighted average: s[0] = x[0], s[t] = alpha*x[t] + (1-alpha)*s[t-1].

    alpha near 1 follows the latest value closely; near 0 it reacts slowly.
    O(n). Same as pandas ewm(alpha=alpha, adjust=False).mean().
    """
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    out: list[float] = []
    for v in values:
        out.append(v if not out else alpha * v + (1 - alpha) * out[-1])
    return out


def linear_trend(values: Sequence[float], x: Sequence[float] | None = None) -> tuple[float, float]:
    """Least-squares line y = slope * x + intercept. Returns (slope, intercept). O(n).

    x defaults to 0, 1, 2, ... (equally spaced seasons). Pass x to use real years.
    slope = sum((x - mean_x) * (y - mean_y)) / sum((x - mean_x) ** 2)
    """
    n = len(values)
    if x is None:
        x = range(n)
    if len(x) != n:
        raise ValueError("x and values must have the same length")
    if n < 2:
        raise ValueError("need at least 2 points to fit a trend")
    mean_x = sum(x) / n
    mean_y = sum(values) / n
    sxx = sum((xi - mean_x) ** 2 for xi in x)
    if sxx == 0:
        raise ValueError("x values are all identical, the slope is undefined")
    sxy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, values))
    slope = sxy / sxx
    return slope, mean_y - slope * mean_x
