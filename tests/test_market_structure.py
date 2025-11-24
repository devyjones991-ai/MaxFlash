"""
Tests for Market Structure analyzer.
"""

import unittest

import numpy as np
import pandas as pd

from indicators.smart_money.market_structure import MarketStructureAnalyzer


class TestMarketStructure(unittest.TestCase):
    """Test Market Structure analysis."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = MarketStructureAnalyzer(swing_lookback=5)

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

    def test_analyze_market_structure(self):
        """Test market structure analysis."""
        result = self.analyzer.analyze_market_structure(self.dataframe)

        # Check that columns are added
        assert "swing_high" in result.columns
        assert "swing_low" in result.columns
        assert "market_structure" in result.columns
        assert "bos_detected" in result.columns
        assert "choch_detected" in result.columns

    def test_swing_detection(self):
        """Test swing high/low detection."""
        result = self.analyzer.analyze_market_structure(self.dataframe)

        swing_highs = result["swing_high"].dropna()
        swing_lows = result["swing_low"].dropna()

        # Should detect some swings
        assert isinstance(swing_highs, pd.Series)
        assert isinstance(swing_lows, pd.Series)

    def test_trend_determination(self):
        """Test trend determination."""
        result = self.analyzer.analyze_market_structure(self.dataframe)

        trend = result["market_structure"].iloc[-1]

        # Trend should be one of: bullish, bearish, range
        assert trend in ["bullish", "bearish", "range"]

    def test_get_market_structure_summary(self):
        """Test getting market structure summary."""
        result = self.analyzer.analyze_market_structure(self.dataframe)

        summary = self.analyzer.get_market_structure_summary(result)

        assert "trend" in summary
        assert "bos_detected" in summary
        assert "choch_detected" in summary


if __name__ == "__main__":
    unittest.main()
