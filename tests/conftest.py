"""
Pytest configuration and fixtures.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_dataframe():
    """Create sample OHLCV dataframe for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="15T")
    np.random.seed(42)

    return pd.DataFrame(
        {
            "open": np.linspace(100, 110, 100),
            "high": np.linspace(101, 111, 100),
            "low": np.linspace(99, 109, 100),
            "close": np.linspace(100, 110, 100),
            "volume": np.random.uniform(1000, 5000, 100),
        },
        index=dates,
    )


@pytest.fixture
def order_block_pattern():
    """Create dataframe with Order Block pattern."""
    dates = pd.date_range("2024-01-01", periods=30, freq="15T")

    # Consolidation followed by impulse
    prices = [100] * 20  # Consolidation
    prices.extend([100 + i * 0.5 for i in range(1, 11)])  # Impulse

    return pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.002 for p in prices],
            "low": [p * 0.998 for p in prices],
            "close": prices,
            "volume": np.ones(30) * 1000,
        },
        index=dates[:30],
    )
