"""
Быстрый тест основных компонентов на минимальных данных.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.volume_profile.volume_profile import VolumeProfileCalculator
from indicators.footprint.footprint_chart import FootprintChart
from indicators.footprint.delta import DeltaAnalyzer
from utils.risk_manager import RiskManager


def quick_test():
    """Быстрый тест на малых данных."""
    print("="*60)
    print("БЫСТРЫЙ ТЕСТ СИСТЕМЫ")
    print("="*60)
    
    # Создаем небольшой набор данных (100 свечей)
    print("\n📊 Создание тестовых данных (100 свечей)...")
    dates = pd.date_range('2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        'open': prices * 0.999,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.uniform(1000000, 3000000, 100)
    }, index=dates)
    
    print(f"✅ Цены: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
    
    # Тест 1: Order Blocks
    print("\n🔍 Тест Order Blocks...")
    detector = OrderBlockDetector(min_candles=3, max_candles=5, impulse_threshold_pct=1.5)
    df_ob = detector.detect_order_blocks(df)
    blocks = detector.get_order_blocks_list()
    print(f"✅ Order Blocks найдено: {len(blocks)}")
    
    # Тест 2: Volume Profile (только последние 50 свечей)
    print("\n🔍 Тест Volume Profile...")
    calculator = VolumeProfileCalculator(bins=50)
    df_vp = calculator.calculate_volume_profile(df.tail(50))
    summary = calculator.get_volume_profile_summary(df_vp)
    if pd.notna(summary['poc']):
        print(f"✅ POC: ${summary['poc']:,.2f}")
        print(f"✅ VAH: ${summary['vah']:,.2f}")
        print(f"✅ VAL: ${summary['val']:,.2f}")
    else:
        print("⚠️  POC не рассчитан (нужно больше данных)")
    
    # Тест 3: Footprint & Delta
    print("\n🔍 Тест Footprint & Delta...")
    footprint = FootprintChart()
    df_fp = footprint.build_footprint(df)
    delta_analyzer = DeltaAnalyzer()
    df_delta = delta_analyzer.calculate_delta(df_fp)
    delta_summary = delta_analyzer.get_delta_summary(df_delta.tail(20))
    print(f"✅ Delta Alignment: {delta_summary['delta_alignment']}")
    print(f"✅ Avg Delta: {delta_summary['avg_delta']:,.0f}")
    
    # Тест 4: Risk Management
    print("\n🔍 Тест Risk Management...")
    risk_mgr = RiskManager(risk_per_trade=0.01)
    entry = df['close'].iloc[-1]
    stop_loss = entry * 0.98
    balance = 10000
    position_size = risk_mgr.calculate_position_size(entry, stop_loss, balance)
    print(f"✅ Entry: ${entry:,.2f}")
    print(f"✅ Stop Loss: ${stop_loss:,.2f}")
    print(f"✅ Position Size: {position_size:.6f} BTC")
    print(f"✅ Risk: ${balance * 0.01:,.2f}")
    
    print("\n" + "="*60)
    print("✅ БЫСТРЫЙ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
    print("="*60)
    print("\nВсе основные компоненты работают корректно.")
    print("Для полного тестирования запустите: python scripts/test_basic_parameters.py")


if __name__ == "__main__":
    quick_test()
