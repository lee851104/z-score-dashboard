from dataclasses import replace
from pathlib import Path

import pytest

from zscore_dashboard.settings import load_settings


@pytest.mark.parametrize(
    "field,value",
    [
        ("ma_period", 1),
        ("slope_window", 0),
        ("trading_days", 1),
        ("band_sigma", 0),
        ("band_sigma", float("inf")),
    ],
)
def test_invalid_indicator_settings(settings, field, value):
    with pytest.raises(ValueError):
        replace(settings.indicators, **{field: value})


def test_explicit_config_and_environment_override(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "configs/dashboard.toml"
    custom = tmp_path / "custom.toml"
    custom.write_text(source.read_text().replace("ma_period = 200", "ma_period = 50"))
    monkeypatch.setenv("ZSCORE_CONFIG", str(custom))
    assert load_settings().indicators.ma_period == 50
    assert load_settings(source).indicators.ma_period == 200


def test_unknown_setting_is_not_silently_ignored(tmp_path):
    custom = tmp_path / "bad.toml"
    custom.write_text("[typo]\nvalue = 1\n")
    with pytest.raises(ValueError):
        load_settings(custom)
