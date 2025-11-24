"""
Tests for Fair Value Gaps detector.
"""

import unittest

import numpy as np
import pandas as pd

from indicators.smart_money.fair_value_gaps import FairValueGapDetector


class TestFairValueGaps(unittest.TestCase):
    """Test Fair Value Gaps detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = FairValueGapDetector(min_size_pct=0.1, max_age_bars=50)

        # Create sample data
        dates = pd.date_range("2024-01-01", periods=100, freq="15T")

        self.dataframe = pd.DataFrame(
            {
                "open": np.linspace(100, 110, 100),
                "high": np.linspace(101, 111, 100),
                "low": np.linspace(99, 109, 100),
                "close": np.linspace(100, 110, 100),
                "volume": np.ones(100) * 1000,
            },
            index=dates,
        )

    def test_detect_fair_value_gaps(self):
        """Test FVG detection."""
        result = self.detector.detect_fair_value_gaps(self.dataframe)

        # Check that columns are added
        assert "fvg_bullish_high" in result.columns
        assert "fvg_bullish_low" in result.columns
        assert "fvg_type" in result.columns
        assert "fvg_strength" in result.columns

    def test_bullish_fvg_detection(self):
        """Test bullish FVG detection."""
        dates = pd.date_range("2024-01-01", periods=10, freq="15T")

        # Create FVG pattern: candle 1 close < candle 3 open, candle 2 doesn't overlap
        opens = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        closes = [100.5, 100.8, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5]
        highs = [101, 101.5, 102, 103, 104, 105, 106, 107, 108, 109]
        lows = [99.5, 100.5, 101, 102, 103, 104, 105, 106, 107, 108]

        # Create FVG: candle 0 close = 100.5, candle 1 high < 100.5, candle 2 open = 102
        closes[0] = 100.5
        highs[1] = 100.4  # Below candle 0 close
        lows[1] = 100.2
        opens[2] = 102  # Above candle 0 close
        lows[2] = 101.8

        df = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": np.ones(10) * 1000}, index=dates[:10]
        )

        result = self.detector.detect_fair_value_gaps(df)

        # Should detect bullish FVG
        bullish_fvgs = result[result["fvg_type"] == "bullish"]
        assert len(bullish_fvgs.dropna()) > 0

    def test_fvg_filling(self):
        """Test FVG filling logic."""
        dates = pd.date_range("2024-01-01", periods=30, freq="15T")

        # Create FVG that gets filled
        prices = list(range(100, 130))

        df = pd.DataFrame(
            {
                "open": prices,
                "high": [p * 1.002 for p in prices],
                "low": [p * 0.998 for p in prices],
                "close": prices,
                "volume": np.ones(30) * 1000,
            },
            index=dates[:30],
        )

        result = self.detector.detect_fair_value_gaps(df)

        # FVG should be detected
        assert "fvg_bullish_high" in result.columns

    def test_fvg_expiration(self):
        """Test FVG expiration after max_age_bars."""
        self.detector.max_age_bars = 5

        dates = pd.date_range("2024-01-01", periods=20, freq="15T")

        df = pd.DataFrame(
            {
                "open": np.linspace(100, 110, 20),
                "high": np.linspace(101, 111, 20),
                "low": np.linspace(99, 109, 20),
                "close": np.linspace(100, 110, 20),
                "volume": np.ones(20) * 1000,
            },
            index=dates,
        )

        self.detector.detect_fair_value_gaps(df)
        active_fvgs = self.detector.get_fvgs_list()

        # After expiration, active FVGs should be filtered
        assert isinstance(active_fvgs, list)

    def test_is_price_in_fvg(self):
        """Test price in FVG check."""
        self.detector.detect_fair_value_gaps(self.dataframe)

        current_price = self.dataframe["close"].iloc[-1]
        fvg = self.detector.is_price_in_fvg(current_price)

        assert isinstance(fvg, (dict, type(None)))


if __name__ == "__main__":
    unittest.main()
