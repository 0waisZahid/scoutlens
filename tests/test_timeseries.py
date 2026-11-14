import math
import random

import numpy as np
import pandas as pd
import pytest

from core.timeseries import exponential_smoothing, linear_trend, moving_average


def test_moving_average_small_example():
    out = moving_average([1, 2, 3, 4, 5], window=3)
    assert math.isnan(out[0]) and math.isnan(out[1])
    assert out[2:] == pytest.approx([2.0, 3.0, 4.0])


@pytest.mark.parametrize("window", [1, 2, 5, 20, 99])
def test_moving_average_matches_pandas(window):
    random.seed(window)
    data = [random.uniform(-100, 100) for _ in range(200)]
    expected = pd.Series(data).rolling(window).mean().to_numpy()
    np.testing.assert_allclose(moving_average(data, window), expected, rtol=1e-9, equal_nan=True)


def test_moving_average_window_longer_than_data_is_all_nan():
    assert all(math.isnan(v) for v in moving_average([1, 2, 3], window=10))


def test_moving_average_empty_and_invalid_window():
    assert moving_average([], 3) == []
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 0)


@pytest.mark.parametrize("alpha", [0.1, 0.3, 0.5, 0.9, 1.0])
def test_smoothing_matches_pandas_ewm(alpha):
    random.seed(7)
    data = [random.uniform(0, 50) for _ in range(150)]
    expected = pd.Series(data).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    np.testing.assert_allclose(exponential_smoothing(data, alpha), expected, rtol=1e-9)


def test_smoothing_first_value_and_alpha_one():
    data = [4.0, 8.0, 6.0]
    assert exponential_smoothing(data, 0.5)[0] == 4.0
    assert exponential_smoothing(data, 1.0) == data


def test_smoothing_empty_and_invalid_alpha():
    assert exponential_smoothing([], 0.5) == []
    for bad in (0, -0.1, 1.5):
        with pytest.raises(ValueError):
            exponential_smoothing([1, 2], bad)


def test_trend_perfect_line():
    slope, intercept = linear_trend([1, 3, 5, 7, 9])         # y = 2x + 1
    assert slope == pytest.approx(2.0) and intercept == pytest.approx(1.0)


def test_trend_matches_numpy_polyfit():
    random.seed(3)
    y = [random.uniform(0, 100) for _ in range(60)]
    x = sorted(random.sample(range(2000, 2100), 60))          # uneven spacing, real years
    slope, intercept = linear_trend(y, x)
    ref_slope, ref_intercept = np.polyfit(x, y, 1)
    assert slope == pytest.approx(ref_slope, rel=1e-6)
    assert intercept == pytest.approx(ref_intercept, rel=1e-6, abs=1e-6)


def test_trend_constant_series_has_zero_slope():
    slope, intercept = linear_trend([5, 5, 5, 5])
    assert slope == pytest.approx(0.0) and intercept == pytest.approx(5.0)


def test_trend_input_validation():
    with pytest.raises(ValueError):
        linear_trend([1])                                      # one point
    with pytest.raises(ValueError):
        linear_trend([1, 2, 3], x=[1, 2])                      # length mismatch
    with pytest.raises(ValueError):
        linear_trend([1, 2, 3], x=[4, 4, 4])                   # no spread in x
