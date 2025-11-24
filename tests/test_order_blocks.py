"""
Tests for Order Blocks detector.
"""

import unittest

import numpy as np
import pandas as pd

from indicators.smart_money.order_blocks import OrderBlockDetector


class TestOrderBlocks(unittest.TestCase):
    """Test Order Blocks detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = OrderBlockDetector(min_candles=3, max_candles=5, impulse_threshold_pct=1.5)

        # Create sample data
        dates = pd.date_range("2024-01-01", periods=100, freq="15T")
        np.random.seed(42)

        # Create data with a consolidation followed by impulse
        prices = np.linspace(100, 110, 100)
        prices[20:25] = prices[20]  # Consolidation

        self.dataframe = pd.DataFrame(
            {
                "open": prices,
                "high": prices * 1.001,
                "low": prices * 0.999,
                "close": prices,
                "volume": np.random.uniform(1000, 5000, 100),
            },
            index=dates,
        )

    def test_detect_order_blocks(self):
        """Test Order Blocks detection."""
        result = self.detector.detect_order_blocks(self.dataframe)

        # Check that columns are added
        assert "ob_bullish_high" in result.columns
        assert "ob_bullish_low" in result.columns
        assert "ob_type" in result.columns

    def test_bullish_order_block_detection(self):
        """Test bullish Order Block detection."""
        # Create specific bullish OB pattern
        dates = pd.date_range("2024-01-01", periods=30, freq="15T")

        prices = np.linspace(100, 100, 25)  # Consolidation
        prices = np.append(prices, np.linspace(100, 105, 5))  # Impulse up

        df = pd.DataFrame(
            {
                "open": prices,
                "high": prices * 1.002,
                "low": prices * 0.998,
                "close": prices,
                "volume": np.ones(30) * 1000,
            },
            index=dates[:30],
        )

        result = self.detector.detect_order_blocks(df)

        # Should detect at least one bullish OB
        bullish_obs = result[result["ob_type"] == "bullish"]
        assert len(bullish_obs.dropna()) > 0

    def test_is_price_in_order_block(self):
        """Test price in Order Block check."""
        self.detector.detect_order_blocks(self.dataframe)

        # Check if price is in an OB
        current_price = self.dataframe["close"].iloc[-1]
        ob = self.detector.is_price_in_order_block(current_price)

        # May or may not be in OB depending on data
        # Just check method doesn't error
        assert isinstance(ob, (dict, type(None)))

    def test_get_order_blocks_list(self):
        """Test getting list of active Order Blocks."""
        self.detector.detect_order_blocks(self.dataframe)
        blocks = self.detector.get_order_blocks_list()

        assert isinstance(blocks, list)

    def test_invalidation(self):
        """Test Order Block invalidation."""
        dates = pd.date_range("2024-01-01", periods=50, freq="15T")

        # Create OB pattern
        prices = np.linspace(100, 100, 5)  # Consolidation
        prices = np.append(prices, np.linspace(100, 105, 5))  # Impulse
        prices = np.append(prices, np.linspace(105, 98, 40))  # Price breaks OB

        df = pd.DataFrame(
            {
                "open": prices,
                "high": prices * 1.002,
                "low": prices * 0.998,
                "close": prices,
                "volume": np.ones(50) * 1000,
            },
            index=dates[:50],
        )

        result = self.detector.detect_order_blocks(df)

        # Last price should break bullish OB (close below OB low)
        last_close = df["close"].iloc[-1]
        last_ob_low = result["ob_bullish_low"].iloc[-1]

        if pd.notna(last_ob_low):
            # Price broke OB, so OB should be invalidated
            assert last_close < last_ob_low


if __name__ == "__main__":
    unittest.main()
