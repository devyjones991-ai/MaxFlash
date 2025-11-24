"""
Backtesting script for trading strategies.
Tests ML signals and strategy performance on historical data.
"""

import asyncio
import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ml.lstm_signal_generator import LSTMSignalGenerator
from utils.async_exchange import get_async_exchange
from utils.logger_config import setup_logging

logger = setup_logging()


class SimpleBacktester:
    """
    Simple backtesting engine for strategy validation.
    """

    def __init__(self, initial_capital: float = 10000, fee: float = 0.001):
        """
        Initialize backtester.

        Args:
            initial_capital: Starting capital
            fee: Trading fee (0.1% = 0.001)
        """
        self.initial_capital = initial_capital
        self.fee = fee
        self.capital = initial_capital
        self.position = None
        self.trades = []

    def execute_trade(self, timestamp, action: str, price: float, confidence: float):
        """Execute a trade based on signal."""
        if action == "BUY" and self.position is None and confidence > 0.6:
            # Open long position
            amount = (self.capital * 0.95) / price  # Use 95% of capital
            cost = amount * price * (1 + self.fee)

            if cost <= self.capital:
                self.position = {
                    "type": "LONG",
                    "entry_price": price,
                    "entry_time": timestamp,
                    "amount": amount,
                    "entry_cost": cost,
                }
                self.capital -= cost
                logger.debug(f"[{timestamp}] BUY {amount:.6f} @ ${price:.2f}")

        elif action == "SELL" and self.position is not None:
            # Close long position
            proceeds = self.position["amount"] * price * (1 - self.fee)
            pnl = proceeds - self.position["entry_cost"]
            pnl_pct = (pnl / self.position["entry_cost"]) * 100

            self.trades.append(
                {
                    "entry_time": self.position["entry_time"],
                    "exit_time": timestamp,
                    "entry_price": self.position["entry_price"],
                    "exit_price": price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "duration": (timestamp - self.position["entry_time"]),
                }
            )

            self.capital += proceeds
            logger.debug(f"[{timestamp}] SELL @ ${price:.2f}, P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
            self.position = None

    def get_stats(self) -> dict:
        """Calculate backtest statistics."""
        if len(self.trades) == 0:
            return {"error": "No trades executed"}

        df_trades = pd.DataFrame(self.trades)

        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        winning_trades = len(df_trades[df_trades["pnl"] > 0])
        losing_trades = len(df_trades[df_trades["pnl"] < 0])
        win_rate = (winning_trades / len(df_trades)) * 100 if len(df_trades) > 0 else 0

        avg_win = df_trades[df_trades["pnl"] > 0]["pnl"].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades["pnl"] < 0]["pnl"].mean() if losing_trades > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        max_drawdown = self._calculate_max_drawdown(df_trades)

        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.capital,
            "total_return": total_return,
            "total_trades": len(df_trades),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "avg_trade_duration": df_trades["duration"].mean(),
        }

    def _calculate_max_drawdown(self, df_trades: pd.DataFrame) -> float:
        """Calculate maximum drawdown percentage."""
        cumulative_pnl = df_trades["pnl"].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        max_dd = (drawdown.min() / self.initial_capital) * 100
        return max_dd


async def backtest_strategy(
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
    days: int = 90,
    model_path: str = None,
    initial_capital: float = 10000,
):
    """
    Backtest ML trading strategy.

    Args:
        symbol: Trading pair
        timeframe: Timeframe
        days: Days to backtest
        model_path: Path to trained model
        initial_capital: Starting capital
    """
    logger.info("=" * 80)
    logger.info(f"BACKTESTING: {symbol} ({timeframe})")
    logger.info("=" * 80)

    # Download data
    exchange = await get_async_exchange("binance")
    timeframe_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
    minutes = timeframe_minutes.get(timeframe, 15)
    candles_needed = int((days * 24 * 60) / minutes)

    logger.info(f"Downloading {candles_needed} candles...")
    ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe, limit=min(candles_needed, 1000))

    if not ohlcv_data:
        logger.error("Failed to download data")
        await exchange.close()
        return

    df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    await exchange.close()

    logger.info(f"Downloaded {len(df)} candles from {df.index[0]} to {df.index[-1]}")

    # Initialize ML model
    if model_path and Path(model_path).exists():
        logger.info(f"Loading model from {model_path}")
        signal_generator = LSTMSignalGenerator(model_path=model_path)
    else:
        logger.warning("No trained model found - using untrained model (results will be random)")
        signal_generator = LSTMSignalGenerator()

    # Initialize backtester
    backtester = SimpleBacktester(initial_capital=initial_capital)

    # Run backtest
    logger.info("Running backtest...")
    lookback = signal_generator.lookback

    for i in range(lookback, len(df)):
        # Get historical data up to this point
        hist_data = df.iloc[: i + 1]

        try:
            # Generate signal
            indicators = {"atr": hist_data["close"].iloc[-1] * 0.02}
            signal = signal_generator.generate_signal(hist_data, indicators)

            # Execute trade
            backtester.execute_trade(
                timestamp=hist_data.index[-1],
                action=signal["action"],
                price=hist_data["close"].iloc[-1],
                confidence=signal["confidence"],
            )

        except Exception as e:
            logger.debug(f"Error at index {i}: {e}")
            continue

    # Close any open position
    if backtester.position:
        backtester.execute_trade(timestamp=df.index[-1], action="SELL", price=df["close"].iloc[-1], confidence=1.0)

    # Get results
    stats = backtester.get_stats()

    # Print results
    logger.info("=" * 80)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Period: {df.index[0]} to {df.index[-1]} ({days} days)")
    logger.info(f"Initial Capital: ${stats['initial_capital']:,.2f}")
    logger.info(f"Final Capital: ${stats['final_capital']:,.2f}")
    logger.info(f"Total Return: {stats['total_return']:+.2f}%")
    logger.info("-" * 80)
    logger.info(f"Total Trades: {stats['total_trades']}")
    logger.info(f"Win Rate: {stats['win_rate']:.2f}%")
    logger.info(f"Winning Trades: {stats['winning_trades']}")
    logger.info(f"Losing Trades: {stats['losing_trades']}")
    logger.info(f"Average Win: ${stats['avg_win']:+.2f}")
    logger.info(f"Average Loss: ${stats['avg_loss']:+.2f}")
    logger.info(f"Profit Factor: {stats['profit_factor']:.2f}")
    logger.info(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
    logger.info("=" * 80)

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backtest trading strategy")
    parser.add_argument("--symbol", default="BTC/USDT", help="Trading pair")
    parser.add_argument("--timeframe", default="15m", help="Timeframe")
    parser.add_argument("--days", type=int, default=90, help="Days to backtest")
    parser.add_argument("--model", help="Path to trained model")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")

    args = parser.parse_args()

    asyncio.run(
        backtest_strategy(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            model_path=args.model,
            initial_capital=args.capital,
        )
    )
