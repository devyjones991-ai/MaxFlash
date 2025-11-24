"""
Быстрый тест основных компонентов на минимальных данных.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from indicators.footprint.delta import DeltaAnalyzer
from indicators.footprint.footprint_chart import FootprintChart
from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.volume_profile.volume_profile import VolumeProfileCalculator
from utils.risk_manager import RiskManager


def quick_test():
    """Быстрый тест на малых данных."""

    # Создаем небольшой набор данных (100 свечей)
    dates = pd.date_range("2024-01-01", periods=100, freq="15min")
    np.random.seed(42)

    prices = 50000 + np.cumsum(np.random.randn(100) * 100)

    df = pd.DataFrame(
        {
            "open": prices * 0.999,
            "high": prices * 1.002,
            "low": prices * 0.998,
            "close": prices,
            "volume": np.random.uniform(1000000, 3000000, 100),
        },
        index=dates,
    )

    # Тест 1: Order Blocks
    detector = OrderBlockDetector(min_candles=3, max_candles=5, impulse_threshold_pct=1.5)
    detector.detect_order_blocks(df)
    detector.get_order_blocks_list()

    # Тест 2: Volume Profile (только последние 50 свечей)
    calculator = VolumeProfileCalculator(bins=50)
    df_vp = calculator.calculate_volume_profile(df.tail(50))
    summary = calculator.get_volume_profile_summary(df_vp)
    if pd.notna(summary["poc"]):
        pass
    else:
        pass

    # Тест 3: Footprint & Delta
    footprint = FootprintChart()
    df_fp = footprint.build_footprint(df)
    delta_analyzer = DeltaAnalyzer()
    df_delta = delta_analyzer.calculate_delta(df_fp)
    delta_analyzer.get_delta_summary(df_delta.tail(20))

    # Тест 4: Risk Management
    risk_mgr = RiskManager(risk_per_trade=0.01)
    entry = df["close"].iloc[-1]
    stop_loss = entry * 0.98
    balance = 10000
    risk_mgr.calculate_position_size(entry, stop_loss, balance)


if __name__ == "__main__":
    quick_test()
