"""Validated TOML settings, shared by source checkouts and installed wheels."""

import math
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IndicatorSettings:
    ma_period: int
    slope_window: int
    trading_days: int
    band_sigma: float

    def __post_init__(self):
        for name in ("ma_period", "slope_window", "trading_days"):
            value = getattr(self, name)
            if type(value) is not int or value < 2:
                raise ValueError(f"{name} must be an integer >= 2")
        if not math.isfinite(self.band_sigma) or self.band_sigma <= 0:
            raise ValueError("band_sigma must be finite and positive")


@dataclass(frozen=True)
class MarketSettings:
    search_candidates: int
    search_limit: int
    search_min_score: float

    def __post_init__(self):
        if not 1 <= self.search_limit <= self.search_candidates:
            raise ValueError("search_limit must be between 1 and search_candidates")
        if not math.isfinite(self.search_min_score) or self.search_min_score < 0:
            raise ValueError("search_min_score must be finite and non-negative")


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int

    def __post_init__(self):
        if not self.host or type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("server host and port are invalid")


@dataclass(frozen=True)
class Settings:
    indicators: IndicatorSettings
    market: MarketSettings
    server: ServerSettings


def load_settings(path: str | Path | None = None) -> Settings:
    if path is None:
        path = os.environ.get("ZSCORE_CONFIG")
    if path is None:
        # Wheels/PyInstaller contain dashboard.toml; editable installs use configs/.
        packaged = Path(__file__).with_name("dashboard.toml")
        path = (
            packaged
            if packaged.is_file()
            else (Path(__file__).resolve().parents[2] / "configs" / "dashboard.toml")
        )
    with Path(path).open("rb") as stream:
        data = tomllib.load(stream)
    if set(data) != {"indicators", "market", "server"}:
        raise ValueError("Settings require indicators, market and server sections")
    return Settings(
        indicators=IndicatorSettings(**data["indicators"]),
        market=MarketSettings(**data["market"]),
        server=ServerSettings(**data["server"]),
    )
