"""
Script to run backtesting with walk-forward analysis.
"""
import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.backtest_analyzer import BacktestAnalyzer
import pandas as pd


def run_freqtrade_backtest(
    strategy_name: str = "SMCFootprintStrategy",
    timeframe: str = "15m",
    timerange: str = "20240101-20240301",
    pairs: list = None
):
    """
    Run Freqtrade backtest.
    
    Args:
        strategy_name: Name of the strategy
        timeframe: Trading timeframe
        timerange: Date range for backtest
        pairs: List of trading pairs
    """
    if pairs is None:
        pairs = ["BTC/USDT", "ETH/USDT"]
    
    print(f"Running backtest for {strategy_name}")
    print(f"Timeframe: {timeframe}")
    print(f"Timerange: {timerange}")
    print(f"Pairs: {', '.join(pairs)}")
    
    # Note: This is a wrapper script
    # Actual backtest should be run via Freqtrade CLI:
    # freqtrade backtesting --strategy {strategy_name} --timeframe {timeframe} --timerange {timerange}
    
    print("\nTo run the actual backtest, use:")
    print(f"cd freqtrade")
    print(f"freqtrade backtesting --strategy {strategy_name} --timeframe {timeframe} --timerange {timerange}")
    
    return None


def analyze_backtest_results(results_path: str):
    """
    Analyze backtest results from Freqtrade output.
    
    Args:
        results_path: Path to backtest results JSON
    """
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        analyzer = BacktestAnalyzer()
        
        # Extract trades and equity curve from results
        # Note: Structure depends on Freqtrade output format
        
        print("Backtest results loaded successfully")
        print("Use Freqtrade's built-in analysis or export trades for detailed analysis")
        
    except FileNotFoundError:
        print(f"Results file not found: {results_path}")
    except json.JSONDecodeError:
        print(f"Invalid JSON in results file: {results_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run backtesting analysis')
    parser.add_argument('--strategy', default='SMCFootprintStrategy', help='Strategy name')
    parser.add_argument('--timeframe', default='15m', help='Timeframe')
    parser.add_argument('--timerange', default='20240101-20240301', help='Timerange')
    parser.add_argument('--analyze', help='Path to results JSON to analyze')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_backtest_results(args.analyze)
    else:
        run_freqtrade_backtest(
            strategy_name=args.strategy,
            timeframe=args.timeframe,
            timerange=args.timerange
        )
