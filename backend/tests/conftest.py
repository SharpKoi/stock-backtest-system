"""Shared test fixtures."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.core.database import initialize_database
from app.services.data_manager import DataManager


@pytest.fixture
def tmp_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    initialize_database(path)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def data_manager(tmp_db_path):
    """Create a DataManager with a temporary database."""
    return DataManager(tmp_db_path)


@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV DataFrame for testing."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-02", periods=200, freq="B")
    price = 100.0
    prices = []
    for _ in range(200):
        price += np.random.randn() * 1.5
        prices.append(max(price, 10))

    close = np.array(prices)
    return pd.DataFrame(
        {
            "open": close * (1 + np.random.randn(200) * 0.005),
            "high": close * (1 + np.abs(np.random.randn(200) * 0.01)),
            "low": close * (1 - np.abs(np.random.randn(200) * 0.01)),
            "close": close,
            "volume": np.random.randint(100000, 2000000, 200),
        },
        index=dates,
    )


@pytest.fixture
def sample_csv_content():
    """Generate sample CSV content string."""
    return (
        "date,open,high,low,close,volume\n"
        "2024-01-02,150.0,152.0,149.0,151.0,5000000\n"
        "2024-01-03,151.0,155.0,150.0,154.0,6000000\n"
        "2024-01-04,154.0,156.0,152.0,153.0,4500000\n"
        "2024-01-05,153.0,157.0,152.5,156.0,5500000\n"
        "2024-01-08,156.0,158.0,155.0,157.0,4000000\n"
    )
