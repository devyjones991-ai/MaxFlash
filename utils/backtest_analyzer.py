"""
Backtest analysis and performance metrics module.
Calculates Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor, etc.
"""

import numpy as np
import pandas as pd

try:
    from scipy import stats
except ImportError:
    stats = None  # Optional dependency


class BacktestAnalyzer:
    """
    Analyzes backtest results and calculates performance metrics.
    """

    def __init__(self):
        """Initialize Backtest Analyzer."""
        pass

    def calculate_sharpe_ratio(
        self, returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe Ratio.

        Args:
            returns: Series of returns
            risk_free_rate: Risk-free rate (default 0)
            periods_per_year: Number of trading periods per year

        Returns:
            Sharpe Ratio
        """
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - (risk_free_rate / periods_per_year)

        if excess_returns.std() == 0:
            return 0.0

        sharpe = np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std()
        return sharpe

    def calculate_max_drawdown(self, equity_curve: pd.Series) -> tuple[float, float, pd.Timestamp, pd.Timestamp]:
        """
        Calculate Maximum Drawdown.

        Args:
            equity_curve: Series of equity values

        Returns:
            Tuple of (max_drawdown, max_drawdown_pct, peak_date, trough_date)
        """
        if len(equity_curve) == 0:
            return (0.0, 0.0, None, None)

        # Calculate running maximum
        running_max = equity_curve.expanding().max()

        # Calculate drawdown
        drawdown = equity_curve - running_max
        drawdown_pct = (equity_curve - running_max) / running_max * 100

        # Find maximum drawdown
        max_drawdown = drawdown.min()
        max_drawdown_pct = drawdown_pct.min()

        # Find dates
        trough_idx = drawdown.idxmin()
        peak_idx = running_max[:trough_idx].idxmax() if trough_idx is not None else None

        return (max_drawdown, max_drawdown_pct, peak_idx, trough_idx)

    def calculate_win_rate(self, trades: pd.DataFrame) -> float:
        """
        Calculate win rate.

        Args:
            trades: DataFrame with trades (must have 'profit' or 'profit_abs' column)

        Returns:
            Win rate as percentage (0-100)
        """
        if len(trades) == 0:
            return 0.0

        # Determine profit column
        profit_col = "profit_abs" if "profit_abs" in trades.columns else "profit"

        if profit_col not in trades.columns:
            return 0.0

        winning_trades = (trades[profit_col] > 0).sum()
        total_trades = len(trades)

        return (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0

    def calculate_profit_factor(self, trades: pd.DataFrame) -> float:
        """
        Calculate Profit Factor.

        Args:
            trades: DataFrame with trades (must have 'profit' or 'profit_abs' column)

        Returns:
            Profit Factor (gross profit / gross loss)
        """
        if len(trades) == 0:
            return 0.0

        # Determine profit column
        profit_col = "profit_abs" if "profit_abs" in trades.columns else "profit"

        if profit_col not in trades.columns:
            return 0.0

        gross_profit = trades[trades[profit_col] > 0][profit_col].sum()
        gross_loss = abs(trades[trades[profit_col] < 0][profit_col].sum())

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def calculate_calmar_ratio(self, returns: pd.Series, equity_curve: pd.Series, periods_per_year: int = 252) -> float:
        """
        Calculate Calmar Ratio (Annual Return / Max Drawdown).

        Args:
            returns: Series of returns
            equity_curve: Series of equity values
            periods_per_year: Number of trading periods per year

        Returns:
            Calmar Ratio
        """
        if len(returns) == 0:
            return 0.0

        annual_return = returns.mean() * periods_per_year

        _, max_dd_pct, _, _ = self.calculate_max_drawdown(equity_curve)

        if abs(max_dd_pct) == 0:
            return 0.0

        calmar = annual_return / abs(max_dd_pct) * 100
        return calmar

    def calculate_statistics(
        self, trades: pd.DataFrame, equity_curve: pd.Series, returns: pd.Series, initial_capital: float = 10000
    ) -> dict:
        """
        Calculate comprehensive performance statistics.

        Args:
            trades: DataFrame with trades
            equity_curve: Series of equity values
            returns: Series of returns
            initial_capital: Initial capital

        Returns:
            Dictionary with all performance metrics
        """
        stats_dict = {}

        # Basic metrics
        stats_dict["total_trades"] = len(trades)
        stats_dict["win_rate"] = self.calculate_win_rate(trades)
        stats_dict["profit_factor"] = self.calculate_profit_factor(trades)

        # Returns
        total_return = (
            (equity_curve.iloc[-1] - initial_capital) / initial_capital * 100 if len(equity_curve) > 0 else 0.0
        )
        stats_dict["total_return_pct"] = total_return
        stats_dict["avg_return"] = returns.mean() if len(returns) > 0 else 0.0

        # Risk metrics
        max_dd, max_dd_pct, peak_date, trough_date = self.calculate_max_drawdown(equity_curve)
        stats_dict["max_drawdown"] = max_dd
        stats_dict["max_drawdown_pct"] = max_dd_pct
        stats_dict["drawdown_peak_date"] = peak_date
        stats_dict["drawdown_trough_date"] = trough_date

        # Sharpe and Calmar
        stats_dict["sharpe_ratio"] = self.calculate_sharpe_ratio(returns)
        stats_dict["calmar_ratio"] = self.calculate_calmar_ratio(returns, equity_curve)

        # Trade statistics
        if "profit_abs" in trades.columns or "profit" in trades.columns:
            profit_col = "profit_abs" if "profit_abs" in trades.columns else "profit"
            stats_dict["avg_win"] = (
                trades[trades[profit_col] > 0][profit_col].mean() if len(trades[trades[profit_col] > 0]) > 0 else 0.0
            )
            stats_dict["avg_loss"] = (
                trades[trades[profit_col] < 0][profit_col].mean() if len(trades[trades[profit_col] < 0]) > 0 else 0.0
            )
            stats_dict["largest_win"] = trades[profit_col].max() if len(trades) > 0 else 0.0
            stats_dict["largest_loss"] = trades[profit_col].min() if len(trades) > 0 else 0.0

        # Expectancy
        if stats_dict["total_trades"] > 0:
            stats_dict["expectancy"] = (stats_dict["win_rate"] / 100) * stats_dict["avg_win"] + (
                1 - stats_dict["win_rate"] / 100
            ) * stats_dict["avg_loss"]
        else:
            stats_dict["expectancy"] = 0.0

        return stats_dict

    def walk_forward_analysis(
        self,
        trades_by_period: dict[str, pd.DataFrame],
        equity_by_period: dict[str, pd.Series],
        returns_by_period: dict[str, pd.Series],
    ) -> dict:
        """
        Perform Walk-Forward Analysis.

        Args:
            trades_by_period: Dictionary of trades by period (train/test)
            equity_by_period: Dictionary of equity curves by period
            returns_by_period: Dictionary of returns by period

        Returns:
            Dictionary with walk-forward results
        """
        results = {}

        for period_name in trades_by_period:
            period_stats = self.calculate_statistics(
                trades_by_period[period_name], equity_by_period[period_name], returns_by_period[period_name]
            )
            results[period_name] = period_stats

        # Calculate consistency
        sharpe_ratios = [stats["sharpe_ratio"] for stats in results.values()]
        if sharpe_ratios:
            results["consistency"] = {
                "avg_sharpe": np.mean(sharpe_ratios),
                "std_sharpe": np.std(sharpe_ratios),
                "min_sharpe": np.min(sharpe_ratios),
                "max_sharpe": np.max(sharpe_ratios),
            }

        return results

    def print_performance_report(self, stats: dict):
        """
        Print formatted performance report.

        Args:
            stats: Dictionary with performance statistics
        """
