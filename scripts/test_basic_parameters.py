"""
Тестирование системы на базовых параметрах.
Создает симуляцию торговли на тестовых данных.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from indicators.footprint.delta import DeltaAnalyzer
from indicators.footprint.footprint_chart import FootprintChart
from indicators.smart_money.fair_value_gaps import FairValueGapDetector
from indicators.smart_money.market_structure import MarketStructureAnalyzer
from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.volume_profile.volume_profile import VolumeProfileCalculator
from utils.confluence import ConfluenceCalculator
from utils.risk_manager import RiskManager

try:
    from utils.backtest_analyzer import BacktestAnalyzer
except ImportError:
    # Fallback if dependencies not installed
    BacktestAnalyzer = None


def create_realistic_test_data(days=7, timeframe_minutes=15):
    """
    Создает реалистичные тестовые данные с паттернами Order Blocks и FVG.
    Уменьшено до 7 дней для быстрого тестирования.
    """
    periods = days * 24 * (60 // timeframe_minutes)
    dates = pd.date_range(start="2024-01-01", periods=periods, freq=f"{timeframe_minutes}min")

    np.random.seed(42)
    base_price = 50000  # BTC-like price

    # Создаем тренд с консолидациями и импульсами
    prices = [base_price]
    trend = 1.0

    for i in range(1, periods):
        # Периодически создаем консолидацию (Order Block)
        if i % 200 == 0:
            # Консолидация (маленькие движения)
            change = np.random.uniform(-0.001, 0.001)
            trend = 1.0 if np.random.random() > 0.5 else -1.0
        elif i % 200 == 5:
            # Импульс после консолидации
            change = trend * np.random.uniform(0.015, 0.025)  # 1.5-2.5% импульс
        else:
            # Нормальное движение
            change = np.random.uniform(-0.005, 0.005) * trend

        new_price = prices[-1] * (1 + change)
        prices.append(new_price)

    prices = np.array(prices)

    # Создаем OHLCV
    high_noise = np.random.uniform(1.001, 1.003, periods)
    low_noise = np.random.uniform(0.997, 0.999, periods)

    df = pd.DataFrame(
        {
            "open": prices * 0.9995,
            "high": prices * high_noise,
            "low": prices * low_noise,
            "close": prices,
            "volume": np.random.uniform(1000000, 5000000, periods),
        },
        index=dates,
    )

    return df


def test_order_blocks_detection(df):
    """Тест детекции Order Blocks."""

    detector = OrderBlockDetector(min_candles=3, max_candles=5, impulse_threshold_pct=1.5)

    result = detector.detect_order_blocks(df)
    active_blocks = detector.get_order_blocks_list()

    if active_blocks:
        for _i, _block in enumerate(active_blocks[:3]):
            pass

    return result, active_blocks


def test_volume_profile(df):
    """Тест Volume Profile."""

    calculator = VolumeProfileCalculator(bins=70, value_area_percent=0.70)

    # Используем меньший период для быстрого расчета
    # Используем меньший период для быстрого расчета
    calculator.bins = 50  # Уменьшаем bins для скорости
    result = calculator.calculate_volume_profile(df.tail(200), period=None)  # Весь период, но только последние 200
    summary = calculator.get_volume_profile_summary(result)

    return result, summary


def test_footprint_delta(df):
    """Тест Footprint и Delta."""

    footprint = FootprintChart()
    df_fp = footprint.build_footprint(df)

    delta_analyzer = DeltaAnalyzer()
    df_delta = delta_analyzer.calculate_delta(df_fp)

    summary = delta_analyzer.get_delta_summary(df_delta.tail(100))

    return df_delta, summary


def test_market_structure(df):
    """Тест Market Structure."""

    analyzer = MarketStructureAnalyzer()
    # Используем только последние 500 свечей для скорости
    result = analyzer.analyze_market_structure(df.tail(500))
    summary = analyzer.get_market_structure_summary(result)

    if summary.get("last_swing_high"):
        pass
    if summary.get("last_swing_low"):
        pass

    return result, summary


def test_confluence(ob_blocks, fvg_detector, vp_summary, mp_summary):
    """Тест Confluence."""

    calculator = ConfluenceCalculator(min_signals=3)

    # Получаем FVG
    fvgs = fvg_detector.get_fvgs_list()

    # Создаем структуру для confluence
    volume_profile_dict = {
        "poc": vp_summary["poc"],
        "hvn": vp_summary["hvn"][:5] if vp_summary["hvn"] else [],
        "lvn": vp_summary["lvn"][:5] if vp_summary["lvn"] else [],
    }

    market_profile_dict = {
        "vah": mp_summary.get("mp_vah"),
        "val": mp_summary.get("mp_val"),
        "poc": mp_summary.get("mp_poc"),
    }

    zones = calculator.find_confluence_zones(ob_blocks, fvgs, volume_profile_dict, market_profile_dict)

    if zones:
        for _i, _zone in enumerate(zones[:3]):
            pass

    return zones


def test_risk_management():
    """Тест Risk Management."""

    risk_mgr = RiskManager(
        risk_per_trade=0.01,  # 1%
        max_risk_per_trade=0.02,
        min_risk_reward_ratio=2.0,
    )

    # Тест расчета размера позиции
    entry = 50000
    stop_loss = 49000  # 2% риск
    balance = 10000

    risk_mgr.calculate_position_size(entry, stop_loss, balance)

    # Тест Take Profit
    tp1, tp2 = risk_mgr.calculate_take_profit(entry, stop_loss, hvn_levels=[51000, 52000], direction="long")

    if tp2:
        pass

    # Валидация сделки
    _is_valid, _reason = risk_mgr.validate_trade(entry, stop_loss, tp1)

    return risk_mgr


def simulate_backtest(df):
    """Симуляция бэктеста на тестовых данных."""

    # Создаем симуляцию сделок
    initial_balance = 10000
    trades = []
    equity = [initial_balance]

    # Симуляция сделок (адаптивно к размеру данных)
    np.random.seed(42)
    num_trades = min(10, len(df) // 50)  # Максимум 10 сделок, но не больше чем позволяет размер данных
    for i in range(num_trades):
        idx = min(i * (len(df) // num_trades), len(df) - 1)
        entry_price = df["close"].iloc[idx]
        direction = "long" if np.random.random() > 0.5 else "short"

        if direction == "long":
            entry_price * 0.98
            entry_price * 1.04  # 2:1 R:R
            profit_pct = 0.04 if np.random.random() > 0.4 else -0.02  # 60% win rate
        else:
            entry_price * 1.02
            entry_price * 0.96
            profit_pct = 0.04 if np.random.random() > 0.4 else -0.02

        profit_abs = initial_balance * 0.01 * (profit_pct / 0.02)  # 1% risk

        trades.append(
            {
                "entry_price": entry_price,
                "exit_price": entry_price * (1 + profit_pct),
                "profit_abs": profit_abs,
                "profit": profit_pct,
                "direction": direction,
            }
        )

        equity.append(equity[-1] + profit_abs)

    trades_df = pd.DataFrame(trades)
    equity_series = pd.Series(equity)
    returns = trades_df["profit"]

    # Анализ производительности
    if BacktestAnalyzer:
        analyzer = BacktestAnalyzer()
        stats = analyzer.calculate_statistics(trades_df, equity_series, returns, initial_balance)

    else:
        # Простой расчет без BacktestAnalyzer
        win_rate = (trades_df["profit_abs"] > 0).sum() / len(trades_df) * 100
        total_return = (equity_series.iloc[-1] - initial_balance) / initial_balance * 100
        gross_profit = trades_df[trades_df["profit_abs"] > 0]["profit_abs"].sum()
        gross_loss = abs(trades_df[trades_df["profit_abs"] < 0]["profit_abs"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        stats = {
            "total_trades": len(trades_df),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_return_pct": total_return,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "avg_win": trades_df[trades_df["profit_abs"] > 0]["profit_abs"].mean()
            if len(trades_df[trades_df["profit_abs"] > 0]) > 0
            else 0,
            "avg_loss": trades_df[trades_df["profit_abs"] < 0]["profit_abs"].mean()
            if len(trades_df[trades_df["profit_abs"] < 0]) > 0
            else 0,
        }

    return stats


def main():
    """Главная функция тестирования."""

    # Создаем тестовые данные (уменьшено для быстрого теста)
    df = create_realistic_test_data(days=7, timeframe_minutes=15)

    # Тест 1: Order Blocks
    _df_ob, ob_blocks = test_order_blocks_detection(df)

    # Тест 2: Volume Profile
    _df_vp, vp_summary = test_volume_profile(df)

    # Тест 3: Footprint & Delta
    _df_delta, delta_summary = test_footprint_delta(df)

    # Тест 4: Market Structure
    df_ms, ms_summary = test_market_structure(df)

    # Тест 5: Fair Value Gaps (нужен для confluence)
    fvg_detector = FairValueGapDetector()
    fvg_detector.detect_fair_value_gaps(df)

    # Тест 6: Confluence
    mp_summary = {
        "mp_vah": df_ms["mp_vah"].iloc[-1] if "mp_vah" in df_ms.columns else None,
        "mp_val": df_ms["mp_val"].iloc[-1] if "mp_val" in df_ms.columns else None,
        "mp_poc": df_ms["mp_poc"].iloc[-1] if "mp_poc" in df_ms.columns else None,
    }
    confluence_zones = test_confluence(ob_blocks, fvg_detector, vp_summary, mp_summary)

    # Тест 7: Risk Management
    test_risk_management()

    # Тест 8: Backtest Simulation
    backtest_stats = simulate_backtest(df)

    # Итоговый отчет

    return {
        "order_blocks": ob_blocks,
        "volume_profile": vp_summary,
        "delta": delta_summary,
        "market_structure": ms_summary,
        "confluence_zones": confluence_zones,
        "backtest_stats": backtest_stats,
    }


if __name__ == "__main__":
    results = main()
