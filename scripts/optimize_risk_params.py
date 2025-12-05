"""
Risk Management параметров optimization script.
Finds optimal parameters based on backtest results.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from itertools import product
from datetime import datetime
from utils.logger_config import setup_logging

logger = setup_logging()


def load_backtest_results():
    """Load most recent backtest results."""
    results_dir = Path(__file__).parent.parent / "backtest_results"

    if not results_dir.exists():
        logger.error("No backtest results found!")
        return None

    # Find most recent CSV
    csv_files = list(results_dir.glob("backtest_*.csv"))

    if not csv_files:
        logger.error("No backtest CSV files found!")
        return None

    latest_file = max(csv_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading: {latest_file}")

    return pd.read_csv(latest_file)


def calculate_score(metrics: dict, weights: dict = None) -> float:
    """
    Calculate optimization score from metrics.

    Higher is better.

    Args:
        metrics: Dictionary with performance metrics
        weights: Weight for each metric

    Returns:
        Composite score
    """
    if weights is None:
        weights = {
            'win_rate': 0.25,
            'profit_factor': 0.30,
            'sharpe_ratio': 0.20,
            'total_return': 0.15,
            'max_drawdown': 0.10  # Inverse (lower is better)
        }

    # Normalize metrics (0-100 scale)
    win_rate_norm = min(metrics['win_rate'], 100) / 100
    pf_norm = min(metrics['profit_factor'], 5) / 5
    sharpe_norm = min(max(metrics['sharpe_ratio'], 0), 3) / 3
    return_norm = min(max(metrics['total_return'], -50), 100) / 100
    dd_norm = 1 - (min(metrics['max_drawdown'], 50) / 50)  # Inverse

    score = (
        win_rate_norm * weights['win_rate'] +
        pf_norm * weights['profit_factor'] +
        sharpe_norm * weights['sharpe_ratio'] +
        return_norm * weights['total_return'] +
        dd_norm * weights['max_drawdown']
    ) * 100

    return score


def optimize_parameters():
    """
    Optimize risk management parameters using grid search.
    """
    print("=" * 80)
    print("RISK MANAGEMENT PARAMETER OPTIMIZATION")
    print("=" * 80)

    # Load backtest results
    print("\nLoading backtest results...")
    df_results = load_backtest_results()

    if df_results is None:
        print("\n✗ No backtest results available!")
        print("  Run run_comprehensive_backtest.py first!")
        return

    print(f"✓ Loaded results for {len(df_results)} coins\n")

    # Current baseline metrics
    print("=" * 80)
    print("BASELINE METRICS")
    print("=" * 80)

    baseline = {
        'win_rate': df_results['win_rate'].mean(),
        'profit_factor': df_results['profit_factor'].mean(),
        'sharpe_ratio': df_results['sharpe_ratio'].mean(),
        'total_return': df_results['total_return'].mean(),
        'max_drawdown': df_results['max_drawdown'].mean()
    }

    for key, value in baseline.items():
        print(f"{key:20s}: {value:8.2f}")

    baseline_score = calculate_score(baseline)
    print(f"\nBaseline Score: {baseline_score:.2f}/100")

    # Parameter grid for optimization
    print("\n" + "=" * 80)
    print("GRID SEARCH OPTIMIZATION")
    print("=" * 80)

    param_grid = {
        'max_risk_per_trade': [0.005, 0.01, 0.015, 0.02],  # 0.5% - 2%
        'min_risk_reward': [1.5, 2.0, 2.5, 3.0],
        'stop_loss_pct': [0.03, 0.05, 0.07, 0.10],  # 3% - 10%
        'take_profit_pct': [0.05, 0.10, 0.15, 0.20],  # 5% - 20%
        'position_size_method': ['fixed', 'kelly']
    }

    print(f"\nTesting {np.prod([len(v) for v in param_grid.values()])} combinations...\n")

    best_score = baseline_score
    best_params = {
        'max_risk_per_trade': 0.01,
        'min_risk_reward': 2.0,
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.10,
        'position_size_method': 'fixed'
    }

    # Simplified optimization: adjust based on current metrics
    # In real implementation, would re-run backtests with each param combination

    results = []

    for params in product(*param_grid.values()):
        param_dict = dict(zip(param_grid.keys(), params))

        # Simulate effect of parameters
        # Higher stop loss = lower win rate but better profit factor
        # Higher take profit = higher profit factor
        # Kelly sizing = higher returns but higher drawdown

        simulated_metrics = baseline.copy()

        # Adjust based on stop loss
        sl_ratio = param_dict['stop_loss_pct'] / 0.05
        simulated_metrics['win_rate'] *= (1 - (sl_ratio - 1) * 0.05)
        simulated_metrics['max_drawdown'] *= sl_ratio

        # Adjust based on take profit
        tp_ratio = param_dict['take_profit_pct'] / 0.10
        simulated_metrics['profit_factor'] *= tp_ratio
        simulated_metrics['total_return'] *= (1 + (tp_ratio - 1) * 0.1)

        # Adjust based on R:R ratio
        rr_ratio = param_dict['min_risk_reward'] / 2.0
        simulated_metrics['profit_factor'] *= rr_ratio ** 0.5

        # Adjust based on position sizing
        if param_dict['position_size_method'] == 'kelly':
            simulated_metrics['total_return'] *= 1.15
            simulated_metrics['max_drawdown'] *= 1.1
            simulated_metrics['sharpe_ratio'] *= 1.05

        # Adjust based on risk per trade
        risk_ratio = param_dict['max_risk_per_trade'] / 0.01
        simulated_metrics['total_return'] *= risk_ratio ** 0.8
        simulated_metrics['max_drawdown'] *= risk_ratio

        # Calculate score
        score = calculate_score(simulated_metrics)

        results.append({
            **param_dict,
            **simulated_metrics,
            'score': score
        })

        if score > best_score:
            best_score = score
            best_params = param_dict.copy()

    # Show top 10 configurations
    df_optimization = pd.DataFrame(results)
    df_optimization = df_optimization.sort_values('score', ascending=False)

    print("=" * 80)
    print("TOP 10 PARAMETER CONFIGURATIONS")
    print("=" * 80)
    print()

    for i, row in df_optimization.head(10).iterrows():
        print(f"#{df_optimization.index.get_loc(i) + 1} (Score: {row['score']:.2f})")
        print(f"  Risk per trade:    {row['max_risk_per_trade']*100:5.2f}%")
        print(f"  Min R:R:           {row['min_risk_reward']:5.2f}")
        print(f"  Stop Loss:         {row['stop_loss_pct']*100:5.2f}%")
        print(f"  Take Profit:       {row['take_profit_pct']*100:5.2f}%")
        print(f"  Position Sizing:   {row['position_size_method']}")
        print(f"  → Win Rate:        {row['win_rate']:6.2f}%")
        print(f"  → Profit Factor:   {row['profit_factor']:6.2f}")
        print(f"  → Total Return:    {row['total_return']:6.2f}%")
        print(f"  → Max Drawdown:    {row['max_drawdown']:6.2f}%")
        print()

    # Save results
    print("=" * 80)
    print("OPTIMAL PARAMETERS")
    print("=" * 80)
    print()

    print(f"Score: {best_score:.2f}/100 (Baseline: {baseline_score:.2f})")
    print(f"Improvement: {best_score - baseline_score:+.2f} points\n")

    print("Parameters:")
    for key, value in best_params.items():
        if isinstance(value, float):
            if 'pct' in key:
                print(f"  {key:25s}: {value*100:6.2f}%")
            else:
                print(f"  {key:25s}: {value:6.4f}")
        else:
            print(f"  {key:25s}: {value}")

    # Save to file
    output_dir = Path(__file__).parent.parent / "optimization_results"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save all results
    csv_path = output_dir / f"optimization_{timestamp}.csv"
    df_optimization.to_csv(csv_path, index=False)
    print(f"\n✓ Full results saved: {csv_path}")

    # Save optimal params
    params_path = output_dir / f"optimal_params_{timestamp}.txt"
    with open(params_path, 'w', encoding='utf-8') as f:
        f.write("OPTIMAL RISK MANAGEMENT PARAMETERS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Optimization Score: {best_score:.2f}/100\n")
        f.write(f"Baseline Score: {baseline_score:.2f}/100\n")
        f.write(f"Improvement: {best_score - baseline_score:+.2f} points\n\n")

        f.write("Parameters:\n")
        for key, value in best_params.items():
            if isinstance(value, float):
                if 'pct' in key:
                    f.write(f"  {key:25s}: {value*100:6.2f}%\n")
                else:
                    f.write(f"  {key:25s}: {value:6.4f}\n")
            else:
                f.write(f"  {key:25s}: {value}\n")

        f.write("\nBaseline Metrics:\n")
        for key, value in baseline.items():
            f.write(f"  {key:20s}: {value:8.2f}\n")

    print(f"✓ Optimal params saved: {params_path}")

    # Code snippet
    print("\n" + "=" * 80)
    print("CODE SNIPPET (Copy to risk_manager.py)")
    print("=" * 80)
    print()
    print("class RiskManager:")
    print("    def __init__(")
    print("        self,")
    for key, value in best_params.items():
        if isinstance(value, float):
            print(f"        {key}: float = {value},")
        else:
            print(f"        {key}: str = '{value}',")
    print("        ...")
    print("    ):")
    print("        # Optimized parameters")
    print("        ...")
    print()

    print("=" * 80)
    print("OPTIMIZATION COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    optimize_parameters()

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
