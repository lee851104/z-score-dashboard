import pandas as pd

from zscore_dashboard.features.indicators import compute_indicators


def test_future_prices_cannot_change_past_indicators(prices, settings):
    boundary = 260
    original = compute_indicators(prices, settings.indicators)
    shocked = prices.copy()
    shocked.iloc[boundary:] *= 1000
    changed = compute_indicators(shocked, settings.indicators)
    pd.testing.assert_frame_equal(original.iloc[:boundary], changed.iloc[:boundary])


def test_truncated_history_matches_same_prefix(prices, settings):
    full = compute_indicators(prices, settings.indicators)
    prefix = compute_indicators(prices.iloc[:260], settings.indicators)
    pd.testing.assert_frame_equal(full.iloc[:260], prefix)
