"""
Walk-Forward Backtesting - NO Look-Ahead Bias!

This script implements proper walk-forward analysis:
1. Split data into chunks (e.g., train on 3 months, test on 1 month)
2. Train model ONLY on past data
3. Test on future data (never seen during training)
4. Roll forward and repeat

This prevents data leakage and gives realistic results.

Expected realistic metrics:
- Win Rate: 45-55% (not 100%!)
- Profit Factor: 1.2-2.0 (not 999!)
- Max Drawdown: 10-25%
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ml.lightgbm_model import LightGBMSignalGenerator
from ml.labeling_fixed import calculate_atr, evaluate_barrier_outcome, create_realistic_labels
from utils.logger_config import setup_logging

logger = setup_logging()

# Walk-Forward Configuration
WALK_FORWARD_CONFIG = {
    'timeframe': '1h',
    'total_days': 180,           # 6 months total
    'train_days': 90,            # Train on 3 months
    'test_days': 30,             # Test on 1 month
    'step_days': 30,             # Move forward 1 month each iteration
    'initial_capital': 10000,
    'fee': 0.001,
    'tp_atr_mult': 2.5,
    'sl_atr_mult': 1.5,
    'horizon_bars': 4,
    'position_size': 0.02,
    'min_confidence': 0.50,      # More conservative
    'min_candles': 500,
}

# Top coins to test
TOP_COINS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT",
]


class WalkForwardBacktester:
    """
    Walk-forward backtester with proper train/test separation.
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        fee: float = 0.001,
        tp_atr_mult: float = 2.5,
        sl_atr_mult: float = 1.5,
        horizon_bars: int = 4,
        position_size: float = 0.02,
        min_confidence: float = 0.50,
    ):
        self.initial_capital = initial_capital
        self.fee = fee
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.horizon_bars = horizon_bars
        self.position_size = position_size
        self.min_confidence = min_confidence

    def split_walk_forward(
        self,
        df: pd.DataFrame,
        train_days: int,
        test_days: int,
        step_days: int,
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Split data into walk-forward windows.

        Returns:
            List of (train_df, test_df) tuples
        """
        windows = []

        # Ensure we have datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.error("DataFrame must have DatetimeIndex")
            return windows

        total_hours = len(df)
        train_hours = train_days * 24
        test_hours = test_days * 24
        step_hours = step_days * 24

        start_idx = 0
        while start_idx + train_hours + test_hours <= total_hours:
            train_end_idx = start_idx + train_hours
            test_end_idx = train_end_idx + test_hours

            train_df = df.iloc[start_idx:train_end_idx].copy()
            test_df = df.iloc[train_end_idx:test_end_idx].copy()

            if len(train_df) >= 500 and len(test_df) >= 100:
                windows.append((train_df, test_df))

            start_idx += step_hours

        return windows

    def backtest_window(
        self,
        test_df: pd.DataFrame,
        model: LightGBMSignalGenerator,
        symbol: str = "UNKNOWN",
    ) -> Optional[Dict]:
        """
        Backtest on a single test window.

        Args:
            test_df: Test data (out-of-sample)
            model: Trained model
            symbol: Symbol name

        Returns:
            Metrics dict or None
        """
        # Calculate ATR
        atr = calculate_atr(test_df, period=14)

        # Get predictions
        try:
            predictions, probs = model.predict_batch_with_probs(test_df)
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return None

        # Initialize tracking
        capital = self.initial_capital
        trades = []

        wins = 0
        losses = 0
        no_trades = 0

        i = 0
        while i < len(predictions) - self.horizon_bars:
            pred = predictions[i]

            # Get confidence
            if i < len(probs):
                sell_prob, hold_prob, buy_prob = probs[i]
                if pred == 2:
                    confidence = buy_prob
                elif pred == 0:
                    confidence = sell_prob
                else:
                    confidence = hold_prob
            else:
                confidence = 0.5

            # Filter by confidence
            if confidence < self.min_confidence:
                i += 1
                continue

            # Only trade BUY/SELL
            if pred == 1:
                i += 1
                continue

            current_price = test_df.iloc[i]['close']
            current_atr = atr.iloc[i]

            if pd.isna(current_atr) or current_atr <= 0:
                i += 1
                continue

            # Determine direction
            is_long = (pred == 2)

            if is_long:
                tp_price = current_price + (current_atr * self.tp_atr_mult)
                sl_price = current_price - (current_atr * self.sl_atr_mult)
            else:
                tp_price = current_price - (current_atr * self.tp_atr_mult)
                sl_price = current_price + (current_atr * self.sl_atr_mult)

            # Position size
            risk_amount = capital * self.position_size
            position_value = risk_amount / (self.sl_atr_mult * current_atr / current_price)
            position_value = min(position_value, capital * 0.5)

            # Evaluate outcome (OK to look ahead here - this is test data!)
            future_df = test_df.iloc[i+1:i+1+self.horizon_bars]
            outcome = evaluate_barrier_outcome(
                entry_price=current_price,
                tp_price=tp_price,
                sl_price=sl_price,
                future_ohlcv=future_df,
                is_long=is_long,
            )

            outcome_type = outcome['outcome']

            if outcome_type == 'win':
                pnl_pct = outcome['pnl_percent'] / 100
                pnl = position_value * pnl_pct - (position_value * self.fee * 2)
                wins += 1
                trade_result = 'WIN'
            elif outcome_type == 'lose':
                pnl_pct = outcome['pnl_percent'] / 100
                pnl = position_value * pnl_pct - (position_value * self.fee * 2)
                losses += 1
                trade_result = 'LOSE'
            else:
                pnl_pct = outcome['pnl_percent'] / 100
                pnl = position_value * pnl_pct - (position_value * self.fee * 2)
                no_trades += 1
                trade_result = 'TIMEOUT'

            capital += pnl

            trades.append({
                'bar': i,
                'direction': 'LONG' if is_long else 'SHORT',
                'entry_price': current_price,
                'outcome': trade_result,
                'pnl': pnl,
                'pnl_pct': pnl_pct * 100,
                'confidence': confidence,
            })

            i += self.horizon_bars + 1

        if len(trades) == 0:
            return None

        # Calculate metrics
        df_trades = pd.DataFrame(trades)

        total_return = ((capital - self.initial_capital) / self.initial_capital) * 100
        total_trades = len(trades)
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

        gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            'symbol': symbol,
            'total_return': total_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'timeouts': no_trades,
            'final_capital': capital,
        }

    def walk_forward_backtest(
        self,
        df: pd.DataFrame,
        train_days: int,
        test_days: int,
        step_days: int,
        symbol: str = "UNKNOWN",
    ) -> Optional[Dict]:
        """
        Run walk-forward backtest on a symbol.

        Args:
            df: Full OHLCV DataFrame
            train_days: Training window size
            test_days: Test window size
            step_days: Step size
            symbol: Symbol name

        Returns:
            Aggregated metrics
        """
        windows = self.split_walk_forward(df, train_days, test_days, step_days)

        if len(windows) == 0:
            logger.warning(f"{symbol}: No valid windows")
            return None

        logger.info(f"{symbol}: {len(windows)} walk-forward windows")

        all_results = []

        for window_idx, (train_df, test_df) in enumerate(windows):
            logger.info(f"  Window {window_idx+1}/{len(windows)}: Train {len(train_df)} bars, Test {len(test_df)} bars")

            # Train model on train_df ONLY
            model = LightGBMSignalGenerator()

            try:
                # Use realistic labels (no look-ahead)
                model.train(
                    train_df,
                    num_boost_round=200,
                    test_size=0.2,
                    use_new_features=True,
                    use_barrier_labels=False,  # Use realistic labels!
                )
            except Exception as e:
                logger.error(f"  Training failed: {e}")
                continue

            # Test on test_df
            result = self.backtest_window(test_df, model, symbol)

            if result:
                result['window'] = window_idx
                all_results.append(result)
                logger.info(f"    WR: {result['win_rate']:.1f}%, PF: {result['profit_factor']:.2f}, Ret: {result['total_return']:+.1f}%")

        if len(all_results) == 0:
            return None

        # Aggregate results
        df_results = pd.DataFrame(all_results)

        return {
            'symbol': symbol,
            'avg_return': df_results['total_return'].mean(),
            'avg_win_rate': df_results['win_rate'].mean(),
            'avg_profit_factor': df_results['profit_factor'].mean(),
            'total_trades': df_results['total_trades'].sum(),
            'total_wins': df_results['wins'].sum(),
            'total_losses': df_results['losses'].sum(),
            'windows': len(windows),
            'successful_windows': len(all_results),
        }


def load_data(symbol: str, days_back: int = 180, timeframe: str = '1h') -> Optional[pd.DataFrame]:
    """Load historical data."""
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


def run_walk_forward_backtest(n_coins: int = 10):
    """Main function."""
    config = WALK_FORWARD_CONFIG

    print("=" * 80)
    print("WALK-FORWARD BACKTEST - NO LOOK-AHEAD BIAS!")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Total period: {config['total_days']} days")
    print(f"  Train window: {config['train_days']} days")
    print(f"  Test window: {config['test_days']} days")
    print(f"  Step size: {config['step_days']} days")
    print(f"  Min confidence: {config['min_confidence']}")

    coins = TOP_COINS[:n_coins]
    print(f"\nTesting {len(coins)} coins:")
    for coin in coins:
        print(f"  - {coin}")

    backtester = WalkForwardBacktester(
        initial_capital=config['initial_capital'],
        fee=config['fee'],
        tp_atr_mult=config['tp_atr_mult'],
        sl_atr_mult=config['sl_atr_mult'],
        horizon_bars=config['horizon_bars'],
        position_size=config['position_size'],
        min_confidence=config['min_confidence'],
    )

    all_results = []

    print(f"\n{'='*80}")
    print("BACKTESTING")
    print(f"{'='*80}\n")

    for i, coin in enumerate(coins, 1):
        print(f"[{i}/{len(coins)}] {coin}")

        df = load_data(coin, days_back=config['total_days'], timeframe=config['timeframe'])

        if df is None or len(df) < config['min_candles']:
            print("  [SKIP] Insufficient data\n")
            continue

        result = backtester.walk_forward_backtest(
            df,
            train_days=config['train_days'],
            test_days=config['test_days'],
            step_days=config['step_days'],
            symbol=coin,
        )

        if result:
            all_results.append(result)
            print(f"  ✅ Avg WR: {result['avg_win_rate']:.1f}%, Avg PF: {result['avg_profit_factor']:.2f}, Avg Ret: {result['avg_return']:+.1f}%\n")
        else:
            print("  [SKIP] No results\n")

    # Print summary
    if not all_results:
        print("\n[FAILED] No successful backtests!")
        return

    df_results = pd.DataFrame(all_results)

    print(f"\n{'='*80}")
    print("REALISTIC RESULTS (NO LOOK-AHEAD BIAS)")
    print(f"{'='*80}\n")

    print(f"Tested Symbols: {len(df_results)}")
    print(f"Total Trades: {df_results['total_trades'].sum():,.0f}")
    print(f"\nAverage Metrics:")
    print(f"  Win Rate: {df_results['avg_win_rate'].mean():.1f}% (realistic!)")
    print(f"  Profit Factor: {df_results['avg_profit_factor'].mean():.2f} (realistic!)")
    print(f"  Return: {df_results['avg_return'].mean():+.1f}%")

    print(f"\n{'='*80}")
    print("TOP 5 PERFORMERS")
    print(f"{'='*80}\n")
    top5 = df_results.nlargest(5, 'avg_return')[['symbol', 'avg_return', 'avg_win_rate', 'avg_profit_factor', 'total_trades']]
    print(top5.to_string(index=False))

    # Save results
    output_dir = Path(__file__).parent.parent / "backtest_results"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"walk_forward_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False)

    print(f"\n[OK] Results saved: {csv_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run walk-forward backtest")
    parser.add_argument('--coins', type=int, default=10, help='Number of coins')
    args = parser.parse_args()

    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    run_walk_forward_backtest(n_coins=args.coins)

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
