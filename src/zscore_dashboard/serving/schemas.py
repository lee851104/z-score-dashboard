"""Stable JSON contract consumed by the existing dashboard."""

import numpy as np
import pandas as pd

from zscore_dashboard.settings import IndicatorSettings


def build_response(ticker: str, frame: pd.DataFrame, settings: IndicatorSettings) -> dict:
    close = frame["close"]
    ma200 = frame["ma200"]
    zscore = frame["zscore"]
    upper_band = frame["upper_band"]
    lower_band = frame["lower_band"]
    slope = frame["slope"]
    valid = ma200.notna()
    if not valid.any():
        raise ValueError(f"資料不足 {settings.ma_period} 天，無法計算指標")

    def _ser(s):
        return [None if (v is None or not np.isfinite(v)) else round(float(v), 4) for v in s[valid]]

    dates = [str(d)[:10] for d in close[valid].index]
    close_v = _ser(close)
    ma200_v = _ser(ma200)
    upper_v = _ser(upper_band)
    lower_v = _ser(lower_band)
    zscore_v = _ser(zscore)
    slope_v = _ser(slope)

    last_close = close_v[-1]
    last_ma200 = ma200_v[-1]
    last_zscore = next((v for v in reversed(zscore_v) if v is not None), 0.0)
    last_slope = next((v for v in reversed(slope_v) if v is not None), 0.0)

    abs_z = abs(last_zscore)
    band_label = (
        "> 2.5"
        if abs_z >= 2.5
        else "2.0 to 2.5"
        if abs_z >= 2.0
        else "1.5 to 2.0"
        if abs_z >= 1.5
        else "1.0 to 1.5"
        if abs_z >= 1.0
        else "0 to 1.0"
    )
    slope_label = (
        "STRONG UPTREND" if last_slope > 15 else "UPTREND" if last_slope > 0 else "DOWNTREND"
    )
    zscore_label = "EXTREME" if abs_z >= 2.5 else "ELEVATED" if abs_z >= 1.5 else "NEUTRAL"

    return {
        "ticker": ticker,
        "meta": {
            "price": last_close,
            "last_date": dates[-1],
            "ma200": last_ma200,
            "zscore": round(last_zscore, 2),
            "zscore_label": zscore_label,
            "slope": round(last_slope, 2),
            "slope_label": slope_label,
            "band_label": band_label,
        },
        "price_chart": {
            "dates": dates,
            "close": close_v,
            "ma200": ma200_v,
            "upper_band": upper_v,
            "lower_band": lower_v,
        },
        "slope_chart": {"dates": dates, "slope": slope_v},
        "zscore_chart": {"dates": dates, "zscore": zscore_v},
    }
