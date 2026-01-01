"""
Comprehensive backtesting script for MaxFlash.

Tests strategy on 1h timeframe with barrier-based TP/SL:
- TP hit before SL = WIN
- SL hit before TP = LOSE
- Neither hit = NO_TRADE

Key metrics:
- Win rate: % of trades that hit TP before SL
- Profit factor: gross profit / gross loss
- Max drawdown: largest peak-to-trough decline
- Average R: average reward in terms of risk units
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
from ml.labeling import calculate_atr, evaluate_barrier_outcome
from utils.logger_config import setup_logging

logger = setup_logging()

# Backtest configuration
BACKTEST_CONFIG = {
    'timeframe': '1h',           # 1h timeframe
    'days_back': 180,            # 6 months of data
    'initial_capital': 10000,    # Starting capital
    'fee': 0.001,                # 0.1% fee per trade
    'tp_atr_mult': 2.5,          # TP = entry + 2.5*ATR
    'sl_atr_mult': 1.5,          # SL = entry - 1.5*ATR
    'horizon_bars': 4,           # 4 bars (4 hours) to hit barrier
    'position_size': 0.02,       # 2% of capital per trade
    'min_confidence': 0.45,      # Minimum ML confidence (баланс: больше сделок но качественных)
    'min_candles': 500,          # Minimum data required
}

# Top coins (fallback if universe selector not available)
TOP_COINS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT",
    "ATOM/USDT", "UNI/USDT", "LTC/USDT", "NEAR/USDT", "ARB/USDT",
    "OP/USDT", "APT/USDT", "SUI/USDT", "INJ/USDT", "FET/USDT",
]

# Try to import universe selector
try:
    from utils.universe_selector import get_top_n_pairs
    HAS_UNIVERSE_SELECTOR = True
except ImportError:
    HAS_UNIVERSE_SELECTOR = False


def get_backtest_coins(n: int = 20) -> List[str]:
    """Get coins for backtesting."""
    if HAS_UNIVERSE_SELECTOR:
        try:
            coins = get_top_n_pairs(n=n, force_refresh=True)
            if coins:
                return coins
        except Exception as e:
            logger.warning(f"Universe selector failed: {e}")
    return TOP_COINS[:n]


class BarrierBacktester:
    """
    Backtester with barrier-based TP/SL evaluation.
    
    Trades are evaluated by whether TP is hit before SL within the horizon,
    matching the training labels for consistency.
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        fee: float = 0.001,
        tp_atr_mult: float = 2.5,
        sl_atr_mult: float = 1.5,
        horizon_bars: int = 4,
        position_size: float = 0.02,
        min_confidence: float = 0.55,
    ):
        self.initial_capital = initial_capital
        self.fee = fee
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.horizon_bars = horizon_bars
        self.position_size = position_size
        self.min_confidence = min_confidence

    def backtest_symbol(
        self, 
        df: pd.DataFrame, 
        model: LightGBMSignalGenerator,
        symbol: str = "UNKNOWN"
    ) -> Optional[Dict]:
        """
        Backtest a single symbol with barrier-based evaluation.

        Args:
            df: OHLCV DataFrame
            model: Trained LightGBM model
            symbol: Symbol name for logging

        Returns:
            Backtest metrics dictionary or None if insufficient data
        """
        if len(df) < BACKTEST_CONFIG['min_candles']:
            return None

        # Calculate ATR
        atr = calculate_atr(df, period=14)
        
        # Get predictions with probabilities
        try:
            predictions, probs = model.predict_batch_with_probs(df)
        except AttributeError:
            # Fallback if method doesn't exist
            predictions = model.predict_batch(df)
            # Create dummy probabilities
            probs = np.array([[0.33, 0.34, 0.33]] * len(predictions))
        except Exception as e:
            logger.warning(f"Prediction failed for {symbol}: {e}")
            return None

        # Initialize tracking
        capital = self.initial_capital
        trades = []
        equity_curve = [capital]
        
        # Track barrier outcomes
        wins = 0
        losses = 0
        no_trades = 0
        skipped_low_conf = 0
        
        i = 0
        while i < len(predictions) - self.horizon_bars:
            # Get prediction
            pred = predictions[i] if i < len(predictions) else 1
            
            # Get confidence from probabilities
            # probs[i] = [sell_prob, hold_prob, buy_prob]
            if i < len(probs):
                sell_prob, hold_prob, buy_prob = probs[i]
                if pred == 2:  # BUY
                    confidence = buy_prob
                elif pred == 0:  # SELL
                    confidence = sell_prob
                else:  # HOLD
                    confidence = hold_prob
            else:
                confidence = 0.5
            
            # Filter by confidence
            if confidence < self.min_confidence:
                skipped_low_conf += 1
                equity_curve.append(capital)
                i += 1
                continue
            
            # Only trade on BUY (2) or SELL (0) signals
            if pred == 1:  # HOLD
                equity_curve.append(capital)
                i += 1
                continue
            
            current_price = df.iloc[i]['close']
            current_atr = atr.iloc[i]
            
            if pd.isna(current_atr) or current_atr <= 0:
                equity_curve.append(capital)
                i += 1
                continue
            
            # Determine direction and barriers
            is_long = (pred == 2)  # BUY
            
            if is_long:
                tp_price = current_price + (current_atr * self.tp_atr_mult)
                sl_price = current_price - (current_atr * self.sl_atr_mult)
            else:  # SHORT
                tp_price = current_price - (current_atr * self.tp_atr_mult)
                sl_price = current_price + (current_atr * self.sl_atr_mult)
            
            # Calculate position size
            risk_amount = capital * self.position_size
            position_value = risk_amount / (self.sl_atr_mult * current_atr / current_price)
            position_value = min(position_value, capital * 0.5)  # Max 50% of capital
            
            # Evaluate barrier outcome
            future_df = df.iloc[i+1:i+1+self.horizon_bars]
            outcome = evaluate_barrier_outcome(
                entry_price=current_price,
                tp_price=tp_price,
                sl_price=sl_price,
                future_ohlcv=future_df,
                is_long=is_long,
            )
            
            # Calculate PnL based on outcome
            outcome_type = outcome['outcome']
            
            if outcome_type == 'win':
                # TP hit first
                pnl_pct = outcome['pnl_percent'] / 100
                pnl = position_value * pnl_pct - (position_value * self.fee * 2)
                wins += 1
                trade_result = 'WIN'
            elif outcome_type == 'lose':
                # SL hit first
                pnl_pct = outcome['pnl_percent'] / 100
                pnl = position_value * pnl_pct - (position_value * self.fee * 2)
                losses += 1
                trade_result = 'LOSE'
            else:
                # Neither barrier hit - close at horizon end
                pnl_pct = outcome['pnl_percent'] / 100
                pnl = position_value * pnl_pct - (position_value * self.fee * 2)
                no_trades += 1
                trade_result = 'TIMEOUT'
            
            capital += pnl
            
            trades.append({
                'bar': i,
                'direction': 'LONG' if is_long else 'SHORT',
                'entry_price': current_price,
                'tp_price': tp_price,
                'sl_price': sl_price,
                'outcome': trade_result,
                'pnl': pnl,
                'pnl_pct': pnl_pct * 100,
                'atr': current_atr,
                'capital_after': capital,
            })
            
            equity_curve.append(capital)
            
            # Skip to after horizon (no overlapping trades)
            i += self.horizon_bars + 1

        # Pad equity curve to match df length
        while len(equity_curve) < len(df):
            equity_curve.append(capital)

        if len(trades) == 0:
            return None

        # Calculate metrics
        df_trades = pd.DataFrame(trades)
        
        total_return = ((capital - self.initial_capital) / self.initial_capital) * 100
        total_trades = len(trades)
        
        # Win rate (TP hit before SL)
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        # Profit factor
        gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
        
        # Average R (reward in risk units)
        avg_r = df_trades['pnl_pct'].mean() / (self.sl_atr_mult * 100 / self.tp_atr_mult) if len(df_trades) > 0 else 0
        
        # Max drawdown
        equity_series = pd.Series(equity_curve)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown = abs(drawdown.min())
        
        # Sharpe ratio (annualized)
        if len(df_trades) > 1:
            returns = df_trades['pnl_pct'].values
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365 * 24) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Expectancy
        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if wins > 0 else 0
        avg_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].mean()) if losses > 0 else 0
        expectancy = (win_rate/100 * avg_win) - ((1 - win_rate/100) * avg_loss)

        return {
            'symbol': symbol,
            'total_return': total_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_r': avg_r,
            'expectancy': expectancy,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'timeouts': no_trades,
            'skipped_low_conf': skipped_low_conf,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'final_capital': capital,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
        }


def load_data(symbol: str, days_back: int = 180, timeframe: str = '1h') -> Optional[pd.DataFrame]:
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


def print_report(df_results: pd.DataFrame, config: Dict):
    """Print comprehensive backtest report."""
    print(f"\n{'='*80}")
    print("BACKTEST REPORT - BARRIER-BASED (TP before SL)")
    print(f"{'='*80}")
    
    print(f"\nConfiguration:")
    print(f"  Timeframe:      {config['timeframe']}")
    print(f"  TP Multiplier:  {config['tp_atr_mult']}x ATR")
    print(f"  SL Multiplier:  {config['sl_atr_mult']}x ATR")
    print(f"  Horizon:        {config['horizon_bars']} bars ({config['horizon_bars']}h)")
    print(f"  Position Size:  {config['position_size']*100:.1f}% of capital")
    print(f"  Min Confidence: {config['min_confidence']:.2f}")
    
    print(f"\n{'='*80}")
    print("AGGREGATE METRICS")
    print(f"{'='*80}")
    
    print(f"\nTested Symbols: {len(df_results)}")
    print(f"Total Trades:   {df_results['total_trades'].sum():,.0f}")
    print(f"Skipped (low conf): {df_results['skipped_low_conf'].sum():,.0f}")
    
    print(f"\n{'Metric':<20} {'Mean':>12} {'Median':>12} {'Best':>12} {'Worst':>12}")
    print("-" * 70)
    
    metrics = [
        ('Total Return %', 'total_return'),
        ('Win Rate %', 'win_rate'),
        ('Profit Factor', 'profit_factor'),
        ('Max Drawdown %', 'max_drawdown'),
        ('Sharpe Ratio', 'sharpe_ratio'),
        ('Average R', 'avg_r'),
        ('Expectancy $', 'expectancy'),
    ]
    
    for name, col in metrics:
        mean = df_results[col].mean()
        median = df_results[col].median()
        best = df_results[col].max() if col != 'max_drawdown' else df_results[col].min()
        worst = df_results[col].min() if col != 'max_drawdown' else df_results[col].max()
        print(f"{name:<20} {mean:>12.2f} {median:>12.2f} {best:>12.2f} {worst:>12.2f}")
    
    print(f"\n{'='*80}")
    print("WIN/LOSS BREAKDOWN")
    print(f"{'='*80}")
    
    total_wins = df_results['wins'].sum()
    total_losses = df_results['losses'].sum()
    total_timeouts = df_results['timeouts'].sum()
    total = total_wins + total_losses + total_timeouts
    
    print(f"\n  Wins (TP hit):     {total_wins:>6} ({total_wins/total*100:>5.1f}%)")
    print(f"  Losses (SL hit):   {total_losses:>6} ({total_losses/total*100:>5.1f}%)")
    print(f"  Timeouts:          {total_timeouts:>6} ({total_timeouts/total*100:>5.1f}%)")
    
    print(f"\n{'='*80}")
    print("TOP 10 PERFORMERS")
    print(f"{'='*80}\n")
    
    top10 = df_results.nlargest(10, 'total_return')[
        ['symbol', 'total_return', 'win_rate', 'profit_factor', 'total_trades']
    ]
    print(top10.to_string(index=False))
    
    print(f"\n{'='*80}")
    print("BOTTOM 5 PERFORMERS")
    print(f"{'='*80}\n")
    
    bottom5 = df_results.nsmallest(5, 'total_return')[
        ['symbol', 'total_return', 'win_rate', 'max_drawdown', 'total_trades']
    ]
    print(bottom5.to_string(index=False))
    
    # Quality gates
    print(f"\n{'='*80}")
    print("QUALITY GATES")
    print(f"{'='*80}")
    
    avg_win_rate = df_results['win_rate'].mean()
    avg_pf = df_results['profit_factor'].mean()
    avg_dd = df_results['max_drawdown'].mean()
    profitable_pct = len(df_results[df_results['total_return'] > 0]) / len(df_results) * 100
    
    gates = [
        (f"Win Rate > 50%", avg_win_rate > 50, f"{avg_win_rate:.1f}%"),
        (f"Profit Factor > 1.5", avg_pf > 1.5, f"{avg_pf:.2f}"),
        (f"Max Drawdown < 15%", avg_dd < 15, f"{avg_dd:.1f}%"),
        (f"Profitable Symbols > 60%", profitable_pct > 60, f"{profitable_pct:.1f}%"),
    ]
    
    print()
    for gate_name, passed, value in gates:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {gate_name} (actual: {value})")
    
    print()


def test_multiple_thresholds(
    model: LightGBMSignalGenerator,
    backtester: BarrierBacktester,
    coins: List[str],
    thresholds: List[float] = [0.40, 0.45, 0.50, 0.55],
) -> pd.DataFrame:
    """Тестировать несколько порогов confidence и вернуть результаты."""
    print(f"\n{'='*80}")
    print("ТЕСТИРОВАНИЕ РАЗНЫХ ПОРОГОВ CONFIDENCE")
    print(f"{'='*80}\n")
    
    all_results = []
    
    for threshold in thresholds:
        print(f"\nПорог {threshold:.2f}...")
        backtester.min_confidence = threshold
        
        threshold_results = []
        for symbol in coins:
            df = load_data(symbol, BACKTEST_CONFIG['timeframe'], BACKTEST_CONFIG['days_back'])
            if df is None or len(df) < BACKTEST_CONFIG['min_candles']:
                continue
            
            result = backtester.backtest_symbol(df, model, symbol)
            if result:
                result['threshold'] = threshold
                threshold_results.append(result)
        
        if threshold_results:
            df_threshold = pd.DataFrame(threshold_results)
            aggregated = {
                'threshold': threshold,
                'total_trades': df_threshold['total_trades'].sum(),
                'avg_win_rate': df_threshold['win_rate'].mean(),
                'avg_profit_factor': df_threshold['profit_factor'].mean(),
                'avg_return': df_threshold['total_return'].mean(),
                'total_skipped': df_threshold['skipped_low_conf'].sum(),
            }
            all_results.append(aggregated)
            
            print(f"  Trades: {aggregated['total_trades']:.0f}, "
                  f"WR: {aggregated['avg_win_rate']:.1f}%, "
                  f"PF: {aggregated['avg_profit_factor']:.2f}")
    
    return pd.DataFrame(all_results)


def run_comprehensive_backtest(n_coins: int = 20, test_thresholds: bool = False):
    """Main backtesting function."""
    config = BACKTEST_CONFIG
    
    print("=" * 80)
    print("COMPREHENSIVE BACKTEST - BARRIER-BASED (1h)")
    print("=" * 80)
    print(f"\nTimeframe: {config['timeframe']}")
    print(f"TP/SL: {config['tp_atr_mult']}*ATR / {config['sl_atr_mult']}*ATR")
    print(f"Horizon: {config['horizon_bars']} bars")

    # Load trained model
    model_paths = [
        Path(__file__).parent.parent / "models" / "lightgbm_latest.pkl",
        Path(__file__).parent.parent / "models" / "lightgbm_quick.pkl",
    ]
    
    model_path = None
    for mp in model_paths:
        if mp.exists():
            model_path = mp
            break

    if not model_path:
        print(f"\n[FAILED] Model not found!")
        print("  Please run train_lightgbm.py first!")
        return

    print(f"\n[OK] Loading model: {model_path}")
    model = LightGBMSignalGenerator(model_path=str(model_path))

    # Get coins to backtest
    coins = get_backtest_coins(n=n_coins)
    print(f"[OK] Testing {len(coins)} coins")

    # Initialize backtester
    backtester = BarrierBacktester(
        initial_capital=config['initial_capital'],
        fee=config['fee'],
        tp_atr_mult=config['tp_atr_mult'],
        sl_atr_mult=config['sl_atr_mult'],
        horizon_bars=config['horizon_bars'],
        position_size=config['position_size'],
        min_confidence=config['min_confidence'],
    )

    # Results storage
    all_results = []

    print(f"\n{'='*80}")
    print("BACKTESTING")
    print(f"{'='*80}\n")

    for i, coin in enumerate(coins, 1):
        print(f"[{i:2d}/{len(coins)}] {coin:15s}...", end=" ", flush=True)

        # Load data
        df = load_data(coin, days_back=config['days_back'], timeframe=config['timeframe'])

        if df is None or len(df) < config['min_candles']:
            print("[SKIP] Insufficient data")
            continue

        # Run backtest
        try:
            metrics = backtester.backtest_symbol(df, model, symbol=coin)

            if metrics:
                all_results.append(metrics)
                wr = metrics['win_rate']
                pf = metrics['profit_factor']
                ret = metrics['total_return']
                print(f"[OK] Ret: {ret:+6.1f}% | WR: {wr:4.1f}% | PF: {pf:4.2f} | Trades: {metrics['total_trades']}")
            else:
                print("[SKIP] No trades")

        except Exception as e:
            print(f"[ERROR] {e}")

    # Generate report
    if not all_results:
        print("\n[FAILED] No successful backtests!")
        return

    df_results = pd.DataFrame(all_results)
    
    print_report(df_results, config)
    
    # Тестируем разные пороги если нужно
    if test_thresholds:
        threshold_results = test_multiple_thresholds(
            model,
            backtester,
            coins,
            thresholds=[0.40, 0.45, 0.50, 0.52, 0.55],
        )
        
        if len(threshold_results) > 0:
            print(f"\n{'='*80}")
            print("РЕКОМЕНДАЦИЯ ПО ПОРОГУ CONFIDENCE")
            print(f"{'='*80}\n")
            
            # Ищем оптимальный (WR>50%, PF>1.5, максимум сделок)
            candidates = threshold_results[
                (threshold_results['avg_win_rate'] >= 50) &
                (threshold_results['avg_profit_factor'] >= 1.5)
            ]
            
            if len(candidates) > 0:
                best = candidates.nlargest(1, 'total_trades').iloc[0]
                print(f"Рекомендуемый порог: {best['threshold']:.2f}")
                print(f"  Trades: {best['total_trades']:.0f}")
                print(f"  Win Rate: {best['avg_win_rate']:.1f}%")
                print(f"  Profit Factor: {best['avg_profit_factor']:.2f}")
            else:
                print("Нет порогов, удовлетворяющих критериям (WR>50%, PF>1.5)")
                print("Используйте текущий порог:", config['min_confidence'])

    # Save results
    output_dir = Path(__file__).parent.parent / "backtest_results"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"backtest_barrier_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False)

    print(f"[OK] Results saved: {csv_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run barrier-based backtest")
    parser.add_argument('--coins', type=int, default=20, help='Number of coins to test (default: 20)')
    parser.add_argument('--test-thresholds', action='store_true', help='Test multiple confidence thresholds')
    args = parser.parse_args()
    
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    run_comprehensive_backtest(n_coins=args.coins, test_thresholds=args.test_thresholds)

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
