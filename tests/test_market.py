from types import SimpleNamespace

import pandas as pd
import pytest

from zscore_dashboard.data.market import YahooMarketData, normalize_close


def test_single_row_remains_series(prices):
    result = normalize_close(prices.iloc[:1].to_frame())
    assert isinstance(result, pd.Series)
    assert len(result) == 1


def test_yahoo_multiindex_close(prices):
    raw = prices.to_frame()
    raw.columns = pd.MultiIndex.from_tuples([("Close", "TEST")])
    pd.testing.assert_series_equal(normalize_close(raw), prices.rename("TEST"))


@pytest.mark.parametrize("case", ["missing_close", "unordered", "duplicate", "infinite"])
def test_invalid_market_data_is_rejected(prices, case):
    raw = prices.to_frame()
    if case == "missing_close":
        raw = raw.rename(columns={"Close": "Open"})
    elif case == "unordered":
        raw = raw.iloc[::-1]
    elif case == "duplicate":
        raw = pd.concat([raw.iloc[:1], raw])
    else:
        raw.iloc[0, 0] = float("inf")
    with pytest.raises(ValueError):
        normalize_close(raw)


def test_provider_requests_adjusted_history(monkeypatch, prices, settings):
    calls = []

    def fake_download(*args, **kwargs):
        calls.append((args, kwargs))
        return prices.to_frame()

    monkeypatch.setattr("zscore_dashboard.data.market.yf.download", fake_download)
    YahooMarketData(settings.market).download("NVDA", start="2023-01-01", end="2024-01-01")
    assert calls == [
        (
            ("NVDA",),
            {"start": "2023-01-01", "end": "2024-01-01", "auto_adjust": True, "progress": False},
        )
    ]


def test_search_ranks_symbol_prefix_first(monkeypatch, settings):
    quotes = [
        {"symbol": "OTHER", "longname": "Nvidia supplier", "typeDisp": "Equity"},
        {"symbol": "NVDA", "longname": "NVIDIA Corporation", "typeDisp": "Equity"},
        {"longname": "Missing symbol"},
    ]
    monkeypatch.setattr(
        "zscore_dashboard.data.market.yf.Search", lambda *a, **kw: SimpleNamespace(quotes=quotes)
    )
    result = YahooMarketData(settings.market).search("NVDA")
    assert result[0] == {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "Equity"}
