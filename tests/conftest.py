import numpy as np
import pandas as pd
import pytest

from zscore_dashboard.settings import load_settings


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def prices():
    days = np.arange(320, dtype=float)
    return pd.Series(
        100 + days * 0.2 + np.sin(days / 7) * 4,
        index=pd.bdate_range("2023-01-02", periods=len(days)),
        name="Close",
    )
