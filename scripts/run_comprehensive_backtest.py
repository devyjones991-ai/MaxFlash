"""
Comprehensive backtesting script for MaxFlash.
Tests strategy on 6 months of data across 50 top coins.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timedelta
from ml.lightgbm_model import LightGBMSignalGenerator
from utils.logger_config import setup_logging

logger = setup_logging()

# Top 50 coins (Updated: MATIC->POL, EOS->WIF, RNDR->RENDER)
TOP_50_COINS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "POL/USDT",
    "TRX/USDT", "LINK/USDT", "ATOM/USDT", "UNI/USDT", "LTC/USDT",
    "XLM/USDT", "NEAR/USDT", "ALGO/USDT", "BCH/USDT", "FIL/USDT",
    "ARB/USDT", "OP/USDT", "APT/USDT", "SUI/USDT", "INJ/USDT",
    "SEI/USDT", "RUNE/USDT", "FET/USDT", "GRT/USDT", "SAND/USDT",
    "MANA/USDT", "AXS/USDT", "THETA/USDT", "XTZ/USDT", "WIF/USDT",
    "AAVE/USDT", "MKR/USDT", "SNX/USDT", "CRV/USDT", "LDO/USDT",
    "IMX/USDT", "RENDER/USDT", "FTM/USDT", "APE/USDT", "CHZ/USDT",
    "EGLD/USDT", "FLOW/USDT", "ICP/USDT", "HBAR/USDT", "QNT/USDT"
]


class ComprehensiveBacktester:
    """Backtester with ML signal generation."""

    def __init__(self, initial_capital: float = 10000, fee: float = 0.001):
        self.initial_capital = initial_capital
        self.fee = fee

    def backtest_symbol(self, df: pd.DataFrame, model: LightGBMSignalGenerator) -> dict:
        """
        Backtest a single symbol with ML predictions.

        Args:
            df: OHLCV DataFrame
            model: Trained LightGBM model

        Returns:
            Backtest metrics dictionary
        """
        if len(df) < 100:
            return None

        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = [capital]

        # Generate predictions
        try:
            predictions = model.predict_batch(df)
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return None

        # Simulate trading
        for i in range(1, len(df)):
            current_price = df.iloc[i]['close']
            signal = predictions[i] if i < len(predictions) else 1  # 0=SELL, 1=HOLD, 2=BUY

            # Open position on BUY signal
            if signal == 2 and position is None:
                amount = (capital * 0.95) / current_price
                cost = amount * current_price * (1 + self.fee)

                if cost <= capital:
                    position = {
                        'entry_price': current_price,
                        'entry_idx': i,
                        'amount': amount,
                        'cost': cost
                    }
                    capital -= cost

            # Close position on SELL signal or stop loss
            elif position is not None:
                # Stop loss at -5%
                stop_loss = position['entry_price'] * 0.95

                # Take profit at +10%
                take_profit = position['entry_price'] * 1.10

                should_close = (signal == 0 or
                               current_price <= stop_loss or
                               current_price >= take_profit)

                if should_close:
                    proceeds = position['amount'] * current_price * (1 - self.fee)
                    pnl = proceeds - position['cost']
                    pnl_pct = (pnl / position['cost']) * 100

                    trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'duration': i - position['entry_idx']
                    })

                    capital += proceeds
                    position = None

            # Track equity
            total_equity = capital
            if position is not None:
                total_equity += position['amount'] * current_price * (1 - self.fee)
            equity_curve.append(total_equity)

        # Close any open position
        if position is not None:
            proceeds = position['amount'] * df.iloc[-1]['close'] * (1 - self.fee)
            capital += proceeds

        if len(trades) == 0:
            return None

        # Calculate metrics
        df_trades = pd.DataFrame(trades)

        total_return = ((capital - self.initial_capital) / self.initial_capital) * 100
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        losing_trades = len(df_trades[df_trades['pnl'] < 0])
        win_rate = (winning_trades / len(df_trades)) * 100

        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].mean()) if losing_trades > 0 else 1
        profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if losing_trades > 0 else 999

        # Max drawdown
        equity_series = pd.Series(equity_curve)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown = abs(drawdown.min())

        # Sharpe ratio (simplified)
        returns = df_trades['pnl_pct'].values
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 1 and returns.std() > 0 else 0

        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'final_capital': capital
        }


def load_data(symbol: str, days_back: int = 180, timeframe: str = '15m'):
    """Load historical data for backtesting."""
    try:
        exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        since = int(start_time.timestamp() * 1000)

        all_ohlcv = []

        while since < int(end_time.timestamp() * 1000):
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            exchange.sleep(exchange.rateLimit / 1000)

        if not all_ohlcv:
            return None

        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df

    except Exception as e:
        logger.error(f"Failed to load {symbol}: {e}")
        return None


def run_comprehensive_backtest():
    """Main backtesting function."""
    print("=" * 80)
    print("COMPREHENSIVE BACKTESTING - 6 MONTHS - 50 COINS")
    print("=" * 80)

    # Load trained model
    model_path = Path(__file__).parent.parent / "models" / "lightgbm_latest.pkl"

    if not model_path.exists():
        print(f"\n[FAILED] Model not found: {model_path}")
        print("  Please run train_lightgbm.py first!")
        return

    print(f"\n[OK] Loading model: {model_path}")
    model = LightGBMSignalGenerator(model_path=str(model_path))

    # Initialize backtester
    backtester = ComprehensiveBacktester(initial_capital=10000, fee=0.001)

    # Results storage
    all_results = []

    print(f"\n{'='*80}")
    print("BACKTESTING COINS")
    print(f"{'='*80}\n")

    for i, coin in enumerate(TOP_50_COINS, 1):
        print(f"[{i}/{len(TOP_50_COINS)}] {coin:15s}...", end=" ", flush=True)

        # Load data
        df = load_data(coin, days_back=180, timeframe='15m')

        if df is None or len(df) < 1000:
            print("[SKIP] Insufficient data")
            continue

        # Run backtest
        try:
            metrics = backtester.backtest_symbol(df, model)

            if metrics:
                metrics['coin'] = coin
                all_results.append(metrics)

                print(f"[OK] Return: {metrics['total_return']:+6.2f}% | WR: {metrics['win_rate']:5.1f}% | PF: {metrics['profit_factor']:4.2f}")
            else:
                print("[SKIP] No trades")

        except Exception as e:
            print(f"[ERROR] {e}")

    # Aggregate results
    if not all_results:
        print("\n[FAILED] No successful backtests!")
        return

    df_results = pd.DataFrame(all_results)

    print(f"\n{'='*80}")
    print("AGGREGATE RESULTS")
    print(f"{'='*80}\n")

    print(f"Tested coins: {len(df_results)}/{len(TOP_50_COINS)}")
    print(f"\nAverage Metrics:")
    print(f"  Total Return:    {df_results['total_return'].mean():>8.2f}%")
    print(f"  Win Rate:        {df_results['win_rate'].mean():>8.2f}%")
    print(f"  Profit Factor:   {df_results['profit_factor'].mean():>8.2f}")
    print(f"  Sharpe Ratio:    {df_results['sharpe_ratio'].mean():>8.2f}")
    print(f"  Max Drawdown:    {df_results['max_drawdown'].mean():>8.2f}%")
    print(f"  Total Trades:    {df_results['total_trades'].sum():>8.0f}")

    print(f"\n{'='*80}")
    print("TOP 10 PERFORMERS")
    print(f"{'='*80}\n")

    top10 = df_results.nlargest(10, 'total_return')[['coin', 'total_return', 'win_rate', 'profit_factor', 'sharpe_ratio']]
    print(top10.to_string(index=False))

    print(f"\n{'='*80}")
    print("BOTTOM 10 PERFORMERS")
    print(f"{'='*80}\n")

    bottom10 = df_results.nsmallest(10, 'total_return')[['coin', 'total_return', 'win_rate', 'profit_factor', 'max_drawdown']]
    print(bottom10.to_string(index=False))

    # Save results
    output_dir = Path(__file__).parent.parent / "backtest_results"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"backtest_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False)

    print(f"\n[OK] Results saved: {csv_path}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    profitable_coins = len(df_results[df_results['total_return'] > 0])
    print(f"Profitable coins: {profitable_coins}/{len(df_results)} ({profitable_coins/len(df_results)*100:.1f}%)")

    if df_results['win_rate'].mean() > 60:
        print("[PASS] Win rate target ACHIEVED (>60%)")
    else:
        print(f"[FAIL] Win rate target NOT achieved ({df_results['win_rate'].mean():.1f}% < 60%)")

    if df_results['profit_factor'].mean() > 2.5:
        print("[PASS] Profit factor target ACHIEVED (>2.5)")
    else:
        print(f"[FAIL] Profit factor target NOT achieved ({df_results['profit_factor'].mean():.2f} < 2.5)")

    if df_results['max_drawdown'].mean() < 10:
        print("[PASS] Max drawdown target ACHIEVED (<10%)")
    else:
        print(f"[FAIL] Max drawdown target NOT achieved ({df_results['max_drawdown'].mean():.1f}% > 10%)")

    print()


if __name__ == "__main__":
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    run_comprehensive_backtest()

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
