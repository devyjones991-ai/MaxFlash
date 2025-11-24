"""
Quick start guide and example usage.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

from indicators.footprint.delta import DeltaAnalyzer
from indicators.footprint.footprint_chart import FootprintChart
from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.volume_profile.volume_profile import VolumeProfileCalculator


def example_order_blocks():
    """Example: Detect Order Blocks."""

    # Create sample data
    dates = pd.date_range("2024-01-01", periods=100, freq="15T")
    prices = np.linspace(100, 110, 100)
    prices[20:25] = prices[20]  # Consolidation

    df = pd.DataFrame(
        {"open": prices, "high": prices * 1.001, "low": prices * 0.999, "close": prices, "volume": np.ones(100) * 1000},
        index=dates,
    )

    # Detect Order Blocks
    detector = OrderBlockDetector()
    detector.detect_order_blocks(df)

    # Get active blocks
    active_blocks = detector.get_order_blocks_list()
    for _i, _block in enumerate(active_blocks[:3]):  # Show first 3
        pass


def example_volume_profile():
    """Example: Calculate Volume Profile."""

    # Create sample data
    dates = pd.date_range("2024-01-01", periods=100, freq="15T")
    np.random.seed(42)

    df = pd.DataFrame(
        {
            "open": np.linspace(100, 110, 100),
            "high": np.linspace(101, 111, 100),
            "low": np.linspace(99, 109, 100),
            "close": np.linspace(100, 110, 100),
            "volume": np.random.uniform(1000, 5000, 100),
        },
        index=dates,
    )

    # Calculate Volume Profile
    calculator = VolumeProfileCalculator()
    result = calculator.calculate_volume_profile(df)

    calculator.get_volume_profile_summary(result)


def example_footprint_delta():
    """Example: Footprint and Delta Analysis."""

    # Create sample data
    dates = pd.date_range("2024-01-01", periods=50, freq="15T")
    np.random.seed(42)

    df = pd.DataFrame(
        {
            "open": np.linspace(100, 105, 50),
            "high": np.linspace(101, 106, 50),
            "low": np.linspace(99, 104, 50),
            "close": np.linspace(100.5, 105.5, 50),  # Mostly green candles
            "volume": np.random.uniform(1000, 5000, 50),
        },
        index=dates,
    )

    # Build footprint
    footprint_chart = FootprintChart()
    df = footprint_chart.build_footprint(df)

    # Calculate Delta
    delta_analyzer = DeltaAnalyzer()
    df = delta_analyzer.calculate_delta(df)

    delta_analyzer.get_delta_summary(df)


def main():
    """Run all examples."""

    try:
        example_order_blocks()
        example_volume_profile()
        example_footprint_delta()

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
