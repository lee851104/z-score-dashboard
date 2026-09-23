"""Yahoo adapter, search ranking and single-ticker close normalization."""

from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import yfinance as yf

from zscore_dashboard.settings import MarketSettings


def normalize_close(raw: pd.DataFrame) -> pd.Series:
    if "Close" not in raw:
        raise ValueError("行情資料缺少收盤價")
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        if close.shape[1] != 1:
            raise ValueError("請一次查詢一個股票代號")
        close = close.iloc[:, 0]
    if not isinstance(close.index, pd.DatetimeIndex):
        raise ValueError("行情資料缺少日期索引")
    if not close.index.is_monotonic_increasing or not close.index.is_unique:
        raise ValueError("行情日期必須遞增且不可重複")
    close = pd.to_numeric(close, errors="coerce").astype(float)
    if np.isinf(close.to_numpy()).any():
        raise ValueError("行情資料含有無效數值")
    return close


def fuzzy_score(q: str, symbol: str, name: str) -> float:
    q_low = q.lower()
    sym_low = symbol.lower()
    name_low = name.lower()

    # exact prefix on symbol beats everything
    if sym_low.startswith(q_low):
        return 1.0 + (1.0 / max(len(sym_low), 1))

    # substring match in symbol or name
    sym_contains = q_low in sym_low
    name_contains = q_low in name_low

    sym_ratio = SequenceMatcher(None, q_low, sym_low).ratio()
    name_ratio = SequenceMatcher(None, q_low, name_low).ratio()

    # also try matching query against each word in the name
    word_best = max(
        (SequenceMatcher(None, q_low, w).ratio() for w in name_low.split()),
        default=0.0,
    )

    score = max(sym_ratio, name_ratio * 0.85, word_best * 0.80)
    if sym_contains:
        score = max(score, 0.75)
    if name_contains:
        score = max(score, 0.65)
    return score


class YahooMarketData:
    def __init__(self, settings: MarketSettings):
        self.settings = settings

    def download(self, ticker: str, *, start=None, end=None) -> pd.DataFrame:
        return yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)

    def search(self, q: str) -> list[dict]:
        results = yf.Search(q, max_results=self.settings.search_candidates, news_count=0)
        quotes = results.quotes if hasattr(results, "quotes") else []
        scored = []
        for item in quotes:
            symbol = item.get("symbol", "")
            name = item.get("longname") or item.get("shortname") or symbol
            etype = item.get("typeDisp", "")
            if not symbol:
                continue
            score = fuzzy_score(q, symbol, name)
            scored.append((score, {"symbol": symbol, "name": name, "type": etype}))

        scored.sort(key=lambda x: x[0], reverse=True)
        out = [
            item
            for score, item in scored[: self.settings.search_limit]
            if score > self.settings.search_min_score
        ]
        return out
