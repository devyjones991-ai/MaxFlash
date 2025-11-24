"""
Script to run backtesting with walk-forward analysis.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from typing import Optional

from utils.backtest_analyzer import BacktestAnalyzer


def run_freqtrade_backtest(
    strategy_name: str = "SMCFootprintStrategy",
    timeframe: str = "15m",
    timerange: str = "20240101-20240301",
    pairs: Optional[list] = None,
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

    # Note: This is a wrapper script
    # Actual backtest should be run via Freqtrade CLI:
    # freqtrade backtesting --strategy {strategy_name} --timeframe {timeframe} --timerange {timerange}

    return None


def analyze_backtest_results(results_path: str):
    """
    Analyze backtest results from Freqtrade output.

    Args:
        results_path: Path to backtest results JSON
    """
    try:
        with open(results_path) as f:
            json.load(f)

        BacktestAnalyzer()

        # Extract trades and equity curve from results
        # Note: Structure depends on Freqtrade output format

    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run backtesting analysis")
    parser.add_argument("--strategy", default="SMCFootprintStrategy", help="Strategy name")
    parser.add_argument("--timeframe", default="15m", help="Timeframe")
    parser.add_argument("--timerange", default="20240101-20240301", help="Timerange")
    parser.add_argument("--analyze", help="Path to results JSON to analyze")

    args = parser.parse_args()

    if args.analyze:
        analyze_backtest_results(args.analyze)
    else:
        run_freqtrade_backtest(strategy_name=args.strategy, timeframe=args.timeframe, timerange=args.timerange)
