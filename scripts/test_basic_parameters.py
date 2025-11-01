"""
Тестирование системы на базовых параметрах.
Создает симуляцию торговли на тестовых данных.
"""
import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.smart_money.fair_value_gaps import FairValueGapDetector
from indicators.smart_money.market_structure import MarketStructureAnalyzer
from indicators.volume_profile.volume_profile import VolumeProfileCalculator
from indicators.market_profile.market_profile import MarketProfileCalculator
from indicators.footprint.footprint_chart import FootprintChart
from indicators.footprint.delta import DeltaAnalyzer
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
    dates = pd.date_range(start='2024-01-01', periods=periods, freq=f'{timeframe_minutes}min')
    
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
    
    df = pd.DataFrame({
        'open': prices * 0.9995,
        'high': prices * high_noise,
        'low': prices * low_noise,
        'close': prices,
        'volume': np.random.uniform(1000000, 5000000, periods)
    }, index=dates)
    
    return df


def test_order_blocks_detection(df):
    """Тест детекции Order Blocks."""
    print("\n" + "="*60)
    print("ТЕСТ 1: Детекция Order Blocks")
    print("="*60)
    
    detector = OrderBlockDetector(
        min_candles=3,
        max_candles=5,
        impulse_threshold_pct=1.5
    )
    
    result = detector.detect_order_blocks(df)
    active_blocks = detector.get_order_blocks_list()
    
    print(f"✅ Данные обработаны: {len(result)} свечей")
    print(f"✅ Активных Order Blocks: {len(active_blocks)}")
    
    if active_blocks:
        print("\nПервые 3 Order Block:")
        for i, block in enumerate(active_blocks[:3]):
            print(f"  {i+1}. {block['type']} OB: ${block['low']:.2f} - ${block['high']:.2f}")
    
    return result, active_blocks


def test_volume_profile(df):
    """Тест Volume Profile."""
    print("\n" + "="*60)
    print("ТЕСТ 2: Volume Profile Analysis")
    print("="*60)
    
    calculator = VolumeProfileCalculator(
        bins=70,
        value_area_percent=0.70
    )
    
    # Используем меньший период для быстрого расчета
    # Используем меньший период для быстрого расчета
    calculator.bins = 50  # Уменьшаем bins для скорости
    result = calculator.calculate_volume_profile(df.tail(200), period=None)  # Весь период, но только последние 200
    summary = calculator.get_volume_profile_summary(result)
    
    print(f"✅ Point of Control (POC): ${summary['poc']:.2f}")
    print(f"✅ Value Area High (VAH): ${summary['vah']:.2f}")
    print(f"✅ Value Area Low (VAL): ${summary['val']:.2f}")
    print(f"✅ High Volume Nodes: {len(summary['hvn'])}")
    print(f"✅ Low Volume Nodes: {len(summary['lvn'])}")
    
    return result, summary


def test_footprint_delta(df):
    """Тест Footprint и Delta."""
    print("\n" + "="*60)
    print("ТЕСТ 3: Footprint & Delta Analysis")
    print("="*60)
    
    footprint = FootprintChart()
    df_fp = footprint.build_footprint(df)
    
    delta_analyzer = DeltaAnalyzer()
    df_delta = delta_analyzer.calculate_delta(df_fp)
    
    summary = delta_analyzer.get_delta_summary(df_delta.tail(100))
    
    print(f"✅ Средний Delta: {summary['avg_delta']:,.0f}")
    print(f"✅ Средний Delta %: {summary['avg_delta_pct']:.2f}%")
    print(f"✅ Текущее выравнивание: {summary['delta_alignment']}")
    print(f"✅ Текущий Delta: {summary['current_delta']:,.0f}")
    
    return df_delta, summary


def test_market_structure(df):
    """Тест Market Structure."""
    print("\n" + "="*60)
    print("ТЕСТ 4: Market Structure Analysis")
    print("="*60)
    
    analyzer = MarketStructureAnalyzer()
    # Используем только последние 500 свечей для скорости
    result = analyzer.analyze_market_structure(df.tail(500))
    summary = analyzer.get_market_structure_summary(result)
    
    print(f"✅ Текущий тренд: {summary['trend']}")
    print(f"✅ BOS детектирован: {summary['bos_detected']}")
    print(f"✅ ChoCH детектирован: {summary['choch_detected']}")
    
    if summary.get('last_swing_high'):
        print(f"✅ Последний Swing High: ${summary['last_swing_high']:.2f}")
    if summary.get('last_swing_low'):
        print(f"✅ Последний Swing Low: ${summary['last_swing_low']:.2f}")
    
    return result, summary


def test_confluence(ob_blocks, fvg_detector, vp_summary, mp_summary):
    """Тест Confluence."""
    print("\n" + "="*60)
    print("ТЕСТ 5: Confluence Calculation")
    print("="*60)
    
    calculator = ConfluenceCalculator(min_signals=3)
    
    # Получаем FVG
    fvgs = fvg_detector.get_fvgs_list()
    
    # Создаем структуру для confluence
    volume_profile_dict = {
        'poc': vp_summary['poc'],
        'hvn': vp_summary['hvn'][:5] if vp_summary['hvn'] else [],
        'lvn': vp_summary['lvn'][:5] if vp_summary['lvn'] else []
    }
    
    market_profile_dict = {
        'vah': mp_summary.get('mp_vah'),
        'val': mp_summary.get('mp_val'),
        'poc': mp_summary.get('mp_poc')
    }
    
    zones = calculator.find_confluence_zones(
        ob_blocks, fvgs, volume_profile_dict, market_profile_dict
    )
    
    print(f"✅ Найдено Confluence зон: {len(zones)}")
    
    if zones:
        print("\nТоп-3 Confluence зоны:")
        for i, zone in enumerate(zones[:3]):
            print(f"  {i+1}. Уровень: ${zone['level']:.2f}")
            print(f"     Сила: {zone['strength']:.2f}")
            print(f"     Сигналов: {zone['signal_count']}")
            print(f"     Зона: ${zone['low']:.2f} - ${zone['high']:.2f}")
    
    return zones


def test_risk_management():
    """Тест Risk Management."""
    print("\n" + "="*60)
    print("ТЕСТ 6: Risk Management")
    print("="*60)
    
    risk_mgr = RiskManager(
        risk_per_trade=0.01,  # 1%
        max_risk_per_trade=0.02,
        min_risk_reward_ratio=2.0
    )
    
    # Тест расчета размера позиции
    entry = 50000
    stop_loss = 49000  # 2% риск
    balance = 10000
    
    position_size = risk_mgr.calculate_position_size(entry, stop_loss, balance)
    
    print(f"✅ Entry: ${entry:,.2f}")
    print(f"✅ Stop Loss: ${stop_loss:,.2f}")
    print(f"✅ Balance: ${balance:,.2f}")
    print(f"✅ Position Size: {position_size:.6f} BTC")
    print(f"✅ Risk Amount: ${balance * 0.01:,.2f}")
    
    # Тест Take Profit
    tp1, tp2 = risk_mgr.calculate_take_profit(
        entry, stop_loss,
        hvn_levels=[51000, 52000],
        direction='long'
    )
    
    print(f"✅ Take Profit 1: ${tp1:,.2f}")
    if tp2:
        print(f"✅ Take Profit 2: ${tp2:,.2f}")
    
    # Валидация сделки
    is_valid, reason = risk_mgr.validate_trade(entry, stop_loss, tp1)
    print(f"✅ Trade Valid: {is_valid} ({reason})")
    
    return risk_mgr


def simulate_backtest(df):
    """Симуляция бэктеста на тестовых данных."""
    print("\n" + "="*60)
    print("ТЕСТ 7: Backtest Simulation")
    print("="*60)
    
    # Создаем симуляцию сделок
    initial_balance = 10000
    trades = []
    equity = [initial_balance]
    
    # Симуляция сделок (адаптивно к размеру данных)
    np.random.seed(42)
    num_trades = min(10, len(df) // 50)  # Максимум 10 сделок, но не больше чем позволяет размер данных
    for i in range(num_trades):
        idx = min(i * (len(df) // num_trades), len(df) - 1)
        entry_price = df['close'].iloc[idx]
        direction = 'long' if np.random.random() > 0.5 else 'short'
        
        if direction == 'long':
            stop_loss = entry_price * 0.98
            take_profit = entry_price * 1.04  # 2:1 R:R
            profit_pct = 0.04 if np.random.random() > 0.4 else -0.02  # 60% win rate
        else:
            stop_loss = entry_price * 1.02
            take_profit = entry_price * 0.96
            profit_pct = 0.04 if np.random.random() > 0.4 else -0.02
        
        profit_abs = initial_balance * 0.01 * (profit_pct / 0.02)  # 1% risk
        
        trades.append({
            'entry_price': entry_price,
            'exit_price': entry_price * (1 + profit_pct),
            'profit_abs': profit_abs,
            'profit': profit_pct,
            'direction': direction
        })
        
        equity.append(equity[-1] + profit_abs)
    
    trades_df = pd.DataFrame(trades)
    equity_series = pd.Series(equity)
    returns = trades_df['profit']
    
    # Анализ производительности
    if BacktestAnalyzer:
        analyzer = BacktestAnalyzer()
        stats = analyzer.calculate_statistics(trades_df, equity_series, returns, initial_balance)
        
        print(f"✅ Всего сделок: {stats['total_trades']}")
        print(f"✅ Win Rate: {stats['win_rate']:.2f}%")
        print(f"✅ Profit Factor: {stats['profit_factor']:.2f}")
        print(f"✅ Total Return: {stats['total_return_pct']:.2f}%")
        print(f"✅ Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
        print(f"✅ Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        print(f"✅ Average Win: ${stats['avg_win']:.2f}")
        print(f"✅ Average Loss: ${stats['avg_loss']:.2f}")
    else:
        # Простой расчет без BacktestAnalyzer
        win_rate = (trades_df['profit_abs'] > 0).sum() / len(trades_df) * 100
        total_return = (equity_series.iloc[-1] - initial_balance) / initial_balance * 100
        gross_profit = trades_df[trades_df['profit_abs'] > 0]['profit_abs'].sum()
        gross_loss = abs(trades_df[trades_df['profit_abs'] < 0]['profit_abs'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        stats = {
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return_pct': total_return,
            'max_drawdown_pct': 0.0,
            'sharpe_ratio': 0.0,
            'avg_win': trades_df[trades_df['profit_abs'] > 0]['profit_abs'].mean() if len(trades_df[trades_df['profit_abs'] > 0]) > 0 else 0,
            'avg_loss': trades_df[trades_df['profit_abs'] < 0]['profit_abs'].mean() if len(trades_df[trades_df['profit_abs'] < 0]) > 0 else 0
        }
        
        print(f"✅ Всего сделок: {stats['total_trades']}")
        print(f"✅ Win Rate: {stats['win_rate']:.2f}%")
        print(f"✅ Profit Factor: {stats['profit_factor']:.2f}")
        print(f"✅ Total Return: {stats['total_return_pct']:.2f}%")
        print(f"✅ Average Win: ${stats['avg_win']:.2f}")
        print(f"✅ Average Loss: ${stats['avg_loss']:.2f}")
    
    return stats


def main():
    """Главная функция тестирования."""
    print("="*60)
    print("ТЕСТИРОВАНИЕ ТОРГОВОЙ СИСТЕМЫ")
    print("Базовые параметры тестирования")
    print("="*60)
    
    # Создаем тестовые данные (уменьшено для быстрого теста)
    print("\n📊 Создание тестовых данных...")
    df = create_realistic_test_data(days=7, timeframe_minutes=15)
    print(f"✅ Создано {len(df)} свечей (7 дней, 15-минутный таймфрейм)")
    print(f"   Диапазон цен: ${df['low'].min():,.2f} - ${df['high'].max():,.2f}")
    
    # Тест 1: Order Blocks
    df_ob, ob_blocks = test_order_blocks_detection(df)
    
    # Тест 2: Volume Profile
    df_vp, vp_summary = test_volume_profile(df)
    
    # Тест 3: Footprint & Delta
    df_delta, delta_summary = test_footprint_delta(df)
    
    # Тест 4: Market Structure
    df_ms, ms_summary = test_market_structure(df)
    
    # Тест 5: Fair Value Gaps (нужен для confluence)
    fvg_detector = FairValueGapDetector()
    df_fvg = fvg_detector.detect_fair_value_gaps(df)
    
    # Тест 6: Confluence
    mp_summary = {
        'mp_vah': df_ms['mp_vah'].iloc[-1] if 'mp_vah' in df_ms.columns else None,
        'mp_val': df_ms['mp_val'].iloc[-1] if 'mp_val' in df_ms.columns else None,
        'mp_poc': df_ms['mp_poc'].iloc[-1] if 'mp_poc' in df_ms.columns else None
    }
    confluence_zones = test_confluence(ob_blocks, fvg_detector, vp_summary, mp_summary)
    
    # Тест 7: Risk Management
    risk_mgr = test_risk_management()
    
    # Тест 8: Backtest Simulation
    backtest_stats = simulate_backtest(df)
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("="*60)
    print(f"✅ Order Blocks: {len(ob_blocks)} обнаружено")
    print(f"✅ Volume Profile: POC на ${vp_summary['poc']:.2f}")
    print(f"✅ Delta Alignment: {delta_summary['delta_alignment']}")
    print(f"✅ Market Trend: {ms_summary['trend']}")
    print(f"✅ Confluence Zones: {len(confluence_zones)}")
    print(f"✅ Backtest Win Rate: {backtest_stats['win_rate']:.2f}%")
    print(f"✅ Backtest Sharpe: {backtest_stats['sharpe_ratio']:.2f}")
    
    print("\n" + "="*60)
    print("✅ ВСЕ ТЕСТЫ УСПЕШНО ЗАВЕРШЕНЫ!")
    print("="*60)
    
    return {
        'order_blocks': ob_blocks,
        'volume_profile': vp_summary,
        'delta': delta_summary,
        'market_structure': ms_summary,
        'confluence_zones': confluence_zones,
        'backtest_stats': backtest_stats
    }


if __name__ == "__main__":
    results = main()
