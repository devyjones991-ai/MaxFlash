"""
Quick start guide and example usage.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.volume_profile.volume_profile import VolumeProfileCalculator
from indicators.footprint.delta import DeltaAnalyzer
from indicators.footprint.footprint_chart import FootprintChart
import pandas as pd
import numpy as np


def example_order_blocks():
    """Example: Detect Order Blocks."""
    print("\n" + "="*60)
    print("Example: Order Blocks Detection")
    print("="*60)
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100, freq='15T')
    prices = np.linspace(100, 110, 100)
    prices[20:25] = prices[20]  # Consolidation
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': np.ones(100) * 1000
    }, index=dates)
    
    # Detect Order Blocks
    detector = OrderBlockDetector()
    result = detector.detect_order_blocks(df)
    
    print(f"Dataframe shape: {result.shape}")
    print(f"Order Block columns: {[col for col in result.columns if 'ob_' in col]}")
    
    # Get active blocks
    active_blocks = detector.get_order_blocks_list()
    print(f"\nActive Order Blocks: {len(active_blocks)}")
    for i, block in enumerate(active_blocks[:3]):  # Show first 3
        print(f"  Block {i+1}: {block['type']} OB at {block['low']:.2f}-{block['high']:.2f}")


def example_volume_profile():
    """Example: Calculate Volume Profile."""
    print("\n" + "="*60)
    print("Example: Volume Profile Calculation")
    print("="*60)
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100, freq='15T')
    np.random.seed(42)
    
    df = pd.DataFrame({
        'open': np.linspace(100, 110, 100),
        'high': np.linspace(101, 111, 100),
        'low': np.linspace(99, 109, 100),
        'close': np.linspace(100, 110, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    }, index=dates)
    
    # Calculate Volume Profile
    calculator = VolumeProfileCalculator()
    result = calculator.calculate_volume_profile(df)
    
    summary = calculator.get_volume_profile_summary(result)
    
    print(f"Point of Control (POC): {summary['poc']:.2f}")
    print(f"Value Area High (VAH): {summary['vah']:.2f}")
    print(f"Value Area Low (VAL): {summary['val']:.2f}")
    print(f"High Volume Nodes: {len(summary['hvn'])}")
    print(f"Low Volume Nodes: {len(summary['lvn'])}")


def example_footprint_delta():
    """Example: Footprint and Delta Analysis."""
    print("\n" + "="*60)
    print("Example: Footprint & Delta Analysis")
    print("="*60)
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=50, freq='15T')
    np.random.seed(42)
    
    df = pd.DataFrame({
        'open': np.linspace(100, 105, 50),
        'high': np.linspace(101, 106, 50),
        'low': np.linspace(99, 104, 50),
        'close': np.linspace(100.5, 105.5, 50),  # Mostly green candles
        'volume': np.random.uniform(1000, 5000, 50)
    }, index=dates)
    
    # Build footprint
    footprint_chart = FootprintChart()
    df = footprint_chart.build_footprint(df)
    
    # Calculate Delta
    delta_analyzer = DeltaAnalyzer()
    df = delta_analyzer.calculate_delta(df)
    
    summary = delta_analyzer.get_delta_summary(df)
    
    print(f"Average Delta: {summary['avg_delta']:.2f}")
    print(f"Average Delta %: {summary['avg_delta_pct']:.2f}%")
    print(f"Delta Alignment: {summary['delta_alignment']}")
    print(f"Current Delta: {summary['current_delta']:.2f}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Trading System - Quick Start Examples")
    print("="*60)
    
    try:
        example_order_blocks()
        example_volume_profile()
        example_footprint_delta()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("="*60)
        print("\nFor more examples, see:")
        print("- docs/strategy_documentation.md")
        print("- tests/ (for usage examples)")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

