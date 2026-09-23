import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from zscore_dashboard.features.indicators import compute_indicators
from zscore_dashboard.serving.schemas import build_response


def test_known_linear_series(settings):
    config = replace(settings.indicators, ma_period=3, slope_window=3, trading_days=252)
    close = pd.Series(
        [10.0, 11.0, 12.0, 13.0, 14.0, 15.0], index=pd.date_range("2024-01-01", periods=6)
    )
    result = compute_indicators(close, config)
    assert result["ma200"].iloc[-1] == 14
    # Sample std of 13, 14, 15 is 1; trailing MA slope is 1 per observation.
    assert result["zscore"].iloc[-1] == 1
    assert result["upper_band"].iloc[-1] == 15.5
    assert result["lower_band"].iloc[-1] == 12.5
    assert result["slope"].iloc[-1] == pytest.approx(252 / 14 * 100)


def test_warmup_and_input_preserved(prices, settings):
    original = prices.copy(deep=True)
    frame = compute_indicators(prices, settings.indicators)
    assert frame["ma200"].first_valid_index() == prices.index[199]
    assert frame["slope"].first_valid_index() == prices.index[219]
    pd.testing.assert_series_equal(prices, original)


def test_constant_prices_are_json_safe(prices, settings):
    prices[:] = 100
    payload = build_response(
        "FLAT", compute_indicators(prices, settings.indicators), settings.indicators
    )
    assert all(value is None for value in payload["zscore_chart"]["zscore"])
    # Compatibility: the legacy KPI displays 0 if no finite Z-Score is available.
    assert payload["meta"]["zscore"] == 0
    json.dumps(payload, allow_nan=False)


def test_missing_observation_is_not_filled(prices, settings):
    prices.iloc[260] = np.nan
    result = compute_indicators(prices, settings.indicators)
    assert result["ma200"].iloc[260:].isna().all()


def test_insufficient_history(prices, settings):
    frame = compute_indicators(prices.iloc[:199], settings.indicators)
    with pytest.raises(ValueError, match="200"):
        build_response("SHORT", frame, settings.indicators)


def test_response_alignment(prices, settings):
    payload = build_response(
        "TEST", compute_indicators(prices, settings.indicators), settings.indicators
    )
    assert payload["meta"]["last_date"] == str(prices.index[-1].date())
    expected_length = len(prices) - 199
    for chart in ("price_chart", "slope_chart", "zscore_chart"):
        assert all(len(values) == expected_length for values in payload[chart].values())
    json.dumps(payload, allow_nan=False)
