"""Trailing indicators. Values at t use observations at or before t only."""

import numpy as np
import pandas as pd

from zscore_dashboard.settings import IndicatorSettings


def annualized_slope(window: np.ndarray, trading_days: int) -> float:
    if not np.isfinite(window).all() or window[-1] == 0:
        return np.nan
    slope = np.polyfit(np.arange(len(window), dtype=float), window, 1)[0]
    return (slope * trading_days) / window[-1] * 100


def compute_indicators(close: pd.Series, settings: IndicatorSettings) -> pd.DataFrame:
    """Return aligned series without filling missing values or mutating inputs."""
    ma = close.rolling(settings.ma_period).mean()
    std = close.rolling(settings.ma_period).std(ddof=1)
    return pd.DataFrame(
        {
            "close": close,
            "ma200": ma,
            "zscore": (close - ma) / std.replace(0, np.nan),
            "upper_band": ma + settings.band_sigma * std,
            "lower_band": ma - settings.band_sigma * std,
            "slope": ma.rolling(settings.slope_window).apply(
                lambda window: annualized_slope(window, settings.trading_days), raw=True
            ),
        }
    )
