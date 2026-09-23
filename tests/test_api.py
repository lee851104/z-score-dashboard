from dataclasses import replace

import pandas as pd
import pytest

from zscore_dashboard.serving.app import create_app


@pytest.mark.parametrize(
    "environment,expected_host,expected_port",
    [
        ({}, "127.0.0.1", 5050),
        ({"PORT": "10000"}, "0.0.0.0", 10000),
        ({"HOST": "127.0.0.2"}, "127.0.0.2", 5050),
        ({"PORT": "10000", "HOST": "127.0.0.2"}, "127.0.0.2", 10000),
    ],
)
def test_cli_listener_supports_local_and_hosted_startup(
    monkeypatch, environment, expected_host, expected_port
):
    from unittest.mock import Mock

    from zscore_dashboard.serving.app import main

    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    application = Mock()
    monkeypatch.setattr("zscore_dashboard.serving.app.create_app", lambda settings: application)
    main()
    application.run.assert_called_once_with(host=expected_host, port=expected_port, debug=False)


class FakeProvider:
    def __init__(self, frame):
        self.frame = frame
        self.calls = []

    def download(self, ticker, **kwargs):
        self.calls.append((ticker, kwargs))
        return self.frame

    def search(self, query):
        return [{"symbol": "NVDA", "name": "NVIDIA", "type": "Equity"}]


def test_homepage_and_api_contract(prices, settings):
    provider = FakeProvider(prices.to_frame())
    client = create_app(settings, provider).test_client()
    home = client.get("/")
    assert home.status_code == 200
    assert b"200 DMA" in home.data and b"ctrl-ticker" in home.data
    response = client.get("/api/regime?ticker=nvda&start=2023-01-01&end=2025-01-01")
    assert response.status_code == 200
    assert response.headers["Cache-Control"].startswith("no-store")
    assert set(response.json) == {"ticker", "meta", "price_chart", "slope_chart", "zscore_chart"}
    assert provider.calls == [("NVDA", {"start": "2023-01-01", "end": "2025-01-01"})]
    assert client.get("/api/search?q=nvidia").json[0]["symbol"] == "NVDA"
    assert client.get("/api/search?q=").json == []


@pytest.mark.parametrize("query", ["ticker=", "start=bad", "start=2025-01-01&end=2024-01-01"])
def test_invalid_input_never_calls_provider(prices, settings, query):
    provider = FakeProvider(prices.to_frame())
    response = create_app(settings, provider).test_client().get("/api/regime?" + query)
    assert response.status_code == 400
    assert provider.calls == []


@pytest.mark.parametrize("count", [0, 1, 199])
def test_empty_or_short_data(prices, settings, count):
    client = create_app(settings, FakeProvider(prices.iloc[:count].to_frame())).test_client()
    assert client.get("/api/regime").status_code == 400


def test_provider_error_does_not_expose_internal_details(settings):
    class FailedProvider:
        def download(self, *args, **kwargs):
            raise RuntimeError("SECRET_INTERNAL_PATH")

        def search(self, *args):
            raise RuntimeError("SECRET_INTERNAL_PATH")

    client = create_app(settings, FailedProvider()).test_client()
    response = client.get("/api/regime")
    assert response.status_code == 502
    assert b"SECRET_INTERNAL_PATH" not in response.data
    assert client.get("/api/search?q=NVDA").json == []


def test_custom_window_updates_page_labels(settings):
    custom = replace(
        settings, indicators=replace(settings.indicators, ma_period=50, band_sigma=2.0)
    )
    response = create_app(custom, FakeProvider(pd.DataFrame())).test_client().get("/")
    assert b"50 DMA" in response.data
    assert "±2.0σ" in response.text
