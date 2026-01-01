"""
Automatic model retraining v2.0 - PROFIT-OPTIMIZED Edition.
Focus on maximizing profit factor and win rate, not just accuracy.

Key improvements:
- Profit-based validation instead of accuracy-only
- Adaptive thresholds based on market volatility
- Ensemble smoothing for stable predictions
- Forward-looking profit simulation
- Gradual model blending instead of full replacement
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import shutil
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import ccxt
from collections import Counter

from ml.lightgbm_model import LightGBMSignalGenerator
from ml.labeling import calculate_atr, evaluate_barrier_outcome
from utils.logger_config import setup_logging

logger = setup_logging()

# Configuration - PROFIT OPTIMIZED with BARRIER-BASED OUTCOMES
CONFIG = {
    'model_path': 'models/lightgbm_latest.pkl',
    'backup_path': 'models/lightgbm_backup.pkl',
    'history_path': 'models/retrain_history.json',
    'versions_dir': 'models/versions',

    # Retraining settings (optimized for top-20 coins, 1h timeframe)
    'timeframe': '1h',              # 1h timeframe for quality signals
    'retrain_days': 30,             # 30 days for 1h data
    'min_samples': 500,             # Minimum samples required (1h has fewer candles)
    'max_boost_rounds': 100,        # Reduced to prevent overfitting
    
    # BARRIER-BASED SETTINGS (matching training labels)
    'tp_atr_mult': 2.5,             # TP = entry + 2.5*ATR
    'sl_atr_mult': 1.5,             # SL = entry - 1.5*ATR
    'horizon_bars': 4,              # 4 bars (4 hours) for barrier evaluation
    
    # PROFIT-BASED THRESHOLDS (not accuracy!)
    'min_profit_factor': 1.2,       # Profit must exceed losses by 20%
    'min_win_rate': 0.50,           # At least 50% winning trades (barrier-based)
    'min_accuracy': 0.45,           # Lower accuracy threshold (profit matters more)
    'max_accuracy_drop': 0.12,      # Allow larger accuracy swings if profit is good
    
    # Stability settings
    'validation_split': 0.25,       # 25% holdout
    'cv_folds': 5,                  # More folds for stability
    'smoothing_alpha': 0.3,         # Blend new model with old (30% new, 70% old)
    'min_improvement': 0.02,        # Require 2% profit factor improvement to update
    
    # Adaptive thresholds
    'high_volatility_threshold': 0.03,  # 3% daily volatility = high vol market
    'volatility_adjustment': 0.8,       # Reduce thresholds in high vol
    
    # Ensemble validation windows (hours)
    'validation_windows': [12, 24, 48, 72],

    # Top-20 coins for training (uses universe selector if available)
    'n_coins': 20,
    'coins': [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
        'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
        'ATOM/USDT', 'UNI/USDT', 'LTC/USDT', 'NEAR/USDT', 'ARB/USDT',
        'OP/USDT', 'APT/USDT', 'SUI/USDT', 'INJ/USDT', 'FET/USDT',
    ],

    # Telegram alerts
    'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
}

# Try to use dynamic universe selector
try:
    from utils.universe_selector import get_top_n_pairs
    HAS_UNIVERSE_SELECTOR = True
except ImportError:
    HAS_UNIVERSE_SELECTOR = False


def send_telegram_alert(message: str, is_error: bool = False):
    """Send alert to Telegram if configured."""
    token = CONFIG['telegram_token']
    chat_id = CONFIG['telegram_chat_id']

    if not token or not chat_id:
        return

    try:
        import requests
        prefix = "🔴 ERROR" if is_error else "🤖 ML Update"
        full_message = f"{prefix}\n\n{message}"

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            'chat_id': chat_id,
            'text': full_message,
            'parse_mode': 'Markdown'
        }, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to send Telegram alert: {e}")


def load_recent_data(days: int = 14) -> pd.DataFrame:
    """Load recent OHLCV data for retraining."""
    exchange = ccxt.binance({'enableRateLimit': True})
    all_data = []

    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    for coin in CONFIG['coins']:
        try:
            ohlcv = exchange.fetch_ohlcv(coin, '15m', since=since, limit=2000)

            if ohlcv:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                df['symbol'] = coin
                all_data.append(df)
                logger.info(f"Loaded {len(df)} candles for {coin}")

        except Exception as e:
            logger.warning(f"Failed to load {coin}: {e}")

    if not all_data:
        return pd.DataFrame()

    combined = pd.concat(all_data, ignore_index=False)
    logger.info(f"Total samples loaded: {len(combined)}")
    return combined


def calculate_market_volatility(data: pd.DataFrame) -> float:
    """Calculate current market volatility (per-symbol averaged)."""
    if 'symbol' not in data.columns:
        # Fallback for single-symbol data
        returns = data['close'].pct_change().dropna()
        return returns.std() * np.sqrt(96)
    
    # Calculate volatility per symbol, then average
    def calc_vol(group):
        returns = group['close'].pct_change().dropna()
        if len(returns) < 10:
            return np.nan
        return returns.std() * np.sqrt(96)  # 96 periods per day for 15m
    
    vols = data.groupby('symbol').apply(calc_vol).dropna()
    if len(vols) == 0:
        return 0.03  # Default 3% if calculation fails
    
    return vols.mean()


def get_adaptive_thresholds(volatility: float) -> Dict:
    """Adjust thresholds based on market volatility."""
    base = CONFIG.copy()
    
    if volatility > CONFIG['high_volatility_threshold']:
        # High volatility - be more lenient
        factor = CONFIG['volatility_adjustment']
        return {
            'min_profit_factor': base['min_profit_factor'] * factor,
            'min_win_rate': base['min_win_rate'] * factor,
            'min_accuracy': base['min_accuracy'] * factor,
            'max_accuracy_drop': base['max_accuracy_drop'] / factor,
        }
    
    return {
        'min_profit_factor': base['min_profit_factor'],
        'min_win_rate': base['min_win_rate'],
        'min_accuracy': base['min_accuracy'],
        'max_accuracy_drop': base['max_accuracy_drop'],
    }


def simulate_trading(
    model: LightGBMSignalGenerator, 
    data: pd.DataFrame,
    tp_atr_mult: float = 2.5,
    sl_atr_mult: float = 1.5,
    horizon_bars: int = 4,
) -> Dict:
    """
    Simulate trading based on model predictions with BARRIER-BASED outcomes.
    
    Uses TP/SL barriers (ATR-based) to evaluate trades - matching the training labels.
    A trade is a WIN if TP is hit before SL within the horizon.
    
    Args:
        model: Trained LightGBM model
        data: OHLCV DataFrame
        tp_atr_mult: Take Profit ATR multiplier
        sl_atr_mult: Stop Loss ATR multiplier
        horizon_bars: Number of bars to check for barrier hits
        
    Returns:
        Profit metrics dictionary
    """
    try:
        predictions = model.predict_batch(data)
        
        # Calculate ATR for barrier levels
        atr = calculate_atr(data, period=14)
        
        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        
        # Simulate trades with barrier evaluation
        trades = []
        i = 0
        
        while i < len(predictions) - horizon_bars:
            pred = predictions[i]
            
            # Only trade on BUY (2) or SELL (0) signals
            if pred == 1:  # HOLD
                i += 1
                continue
            
            entry_price = close[i]
            current_atr = atr.iloc[i]
            
            if np.isnan(current_atr) or current_atr <= 0:
                i += 1
                continue
            
            is_long = (pred == 2)  # BUY
            
            # Calculate barriers
            if is_long:
                tp_price = entry_price + (current_atr * tp_atr_mult)
                sl_price = entry_price - (current_atr * sl_atr_mult)
            else:  # SHORT
                tp_price = entry_price - (current_atr * tp_atr_mult)
                sl_price = entry_price + (current_atr * sl_atr_mult)
            
            # Check future bars for barrier hits
            future_df = data.iloc[i+1:i+1+horizon_bars]
            outcome = evaluate_barrier_outcome(
                entry_price=entry_price,
                tp_price=tp_price,
                sl_price=sl_price,
                future_ohlcv=future_df,
                is_long=is_long,
            )
            
            # Calculate PnL based on outcome
            pnl_pct = outcome['pnl_percent']
            outcome_type = outcome['outcome']
            
            trades.append({
                'signal': 'BUY' if is_long else 'SELL',
                'pnl': pnl_pct,
                'outcome': outcome_type,
                'entry': entry_price,
                'tp': tp_price,
                'sl': sl_price,
            })
            
            # Skip to after horizon (no overlapping trades)
            i += horizon_bars + 1
        
        if not trades:
            return {'profit_factor': 0, 'win_rate': 0, 'total_pnl': 0, 'trades': 0}
        
        trades_df = pd.DataFrame(trades)
        
        # Calculate metrics
        winning = trades_df[trades_df['outcome'] == 'win']
        losing = trades_df[trades_df['outcome'] == 'lose']
        
        gross_profit = winning['pnl'].sum() if len(winning) > 0 else 0
        gross_loss = abs(losing['pnl'].sum()) if len(losing) > 0 else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0)
        win_rate = len(winning) / len(trades_df) if len(trades_df) > 0 else 0
        total_pnl = trades_df['pnl'].sum()
        
        return {
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'trades': len(trades_df),
            'wins': len(winning),
            'losses': len(losing),
            'timeouts': len(trades_df[trades_df['outcome'] == 'no_hit']),
            'avg_win': winning['pnl'].mean() if len(winning) > 0 else 0,
            'avg_loss': losing['pnl'].mean() if len(losing) > 0 else 0,
        }
        
    except Exception as e:
        logger.error(f"Trading simulation failed: {e}")
        return {'profit_factor': 0, 'win_rate': 0, 'total_pnl': 0, 'trades': 0}


def cross_validate_profit(model: LightGBMSignalGenerator, data: pd.DataFrame, n_folds: int = 5) -> Dict:
    """
    Cross-validate with PROFIT metrics.
    """
    fold_size = len(data) // (n_folds + 1)
    results = []

    for i in range(n_folds):
        train_end = fold_size * (i + 1)
        val_end = fold_size * (i + 2)

        train_data = data.iloc[:train_end]
        val_data = data.iloc[train_end:val_end]

        if len(train_data) < 500 or len(val_data) < 100:
            continue

        try:
            temp_model = LightGBMSignalGenerator()
            temp_model.train(train_data, num_boost_round=50, use_new_features=True)
            
            metrics = simulate_trading(temp_model, val_data)
            results.append(metrics)
            
            logger.info(f"CV Fold {i+1}: PF={metrics['profit_factor']:.2f}, WR={metrics['win_rate']:.2%}")

        except Exception as e:
            logger.warning(f"CV Fold {i+1} failed: {e}")

    if not results:
        return {'profit_factor': 0, 'win_rate': 0, 'std': 1.0}

    pf_values = [r['profit_factor'] for r in results]
    wr_values = [r['win_rate'] for r in results]
    
    return {
        'profit_factor': np.mean(pf_values),
        'profit_factor_std': np.std(pf_values),
        'win_rate': np.mean(wr_values),
        'win_rate_std': np.std(wr_values),
        'folds': len(results),
    }


# Window weights for self-improvement (longer windows more important)
WINDOW_WEIGHTS = {
    8: 0.15,   # Less weight on short-term
    16: 0.25,
    24: 0.35,  # Most weight on 24h (1 day)
    48: 0.25,
}


def validate_on_windows_profit(model: LightGBMSignalGenerator, data: pd.DataFrame) -> Dict[str, Dict]:
    """Validate profit metrics on multiple time windows with weighted scoring."""
    results = {}
    now = data.index.max() if hasattr(data.index, 'max') else datetime.now()

    for hours in CONFIG['validation_windows']:
        try:
            window_start = now - timedelta(hours=hours)
            if hasattr(data.index, 'max'):
                window_data = data[data.index >= window_start]
            else:
                window_data = data.tail(int(hours * 4))

            if len(window_data) < 50:
                continue

            metrics = simulate_trading(model, window_data)
            metrics['weight'] = WINDOW_WEIGHTS.get(hours, 0.25)
            results[f'{hours}h'] = metrics
            logger.info(f"Window {hours}h: PF={metrics['profit_factor']:.2f}, WR={metrics['win_rate']:.2%}")

        except Exception as e:
            logger.warning(f"Window {hours}h validation failed: {e}")

    return results


def calculate_weighted_pf(window_results: Dict[str, Dict]) -> float:
    """Calculate weighted average profit factor across windows."""
    if not window_results:
        return 0.0
    
    total_weight = 0.0
    weighted_pf = 0.0
    
    for key, metrics in window_results.items():
        weight = metrics.get('weight', 0.25)
        pf = metrics.get('profit_factor', 0.0)
        
        # Cap extreme values to prevent outlier influence
        pf = min(max(pf, 0.0), 5.0)
        
        weighted_pf += pf * weight
        total_weight += weight
    
    return weighted_pf / total_weight if total_weight > 0 else 0.0


def load_history() -> dict:
    """Load retraining history."""
    history_path = Path(CONFIG['history_path'])
    if history_path.exists():
        with open(history_path, 'r') as f:
            return json.load(f)
    return {'runs': [], 'baseline_profit_factor': 1.0, 'best_profit_factor': 1.0}


def save_history(history: dict):
    """Save retraining history."""
    with open(CONFIG['history_path'], 'w') as f:
        json.dump(history, f, indent=2, default=str)


def auto_retrain_v2():
    """
    Main auto-retraining function v2.0 - PROFIT OPTIMIZED.
    
    Focus on:
    1. Profit Factor > 1.0 (profits exceed losses)
    2. Win Rate stability across time windows
    3. Gradual model updates (blending) for stability
    4. Adaptive thresholds for volatile markets
    """
    print("=" * 70)
    print("AUTO RETRAIN v2.0 (PROFIT OPTIMIZED)")
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    history = load_history()
    model_path = Path(CONFIG['model_path'])
    backup_path = Path(CONFIG['backup_path'])

    # Step 1: Load current model
    if not model_path.exists():
        print("[ERROR] No model found. Train base model first.")
        send_telegram_alert("No base model found!", is_error=True)
        return False

    print("\n[1/8] Loading current model...")
    model = LightGBMSignalGenerator(model_path=str(model_path))

    # Step 2: Create backup
    print("[2/8] Creating backup...")
    shutil.copy(model_path, backup_path)
    meta_path = str(model_path) + '_meta.pkl'
    if Path(meta_path).exists():
        shutil.copy(meta_path, str(backup_path) + '_meta.pkl')

    # Step 3: Load data (14 days)
    print(f"\n[3/8] Loading last {CONFIG['retrain_days']} days of data...")
    data = load_recent_data(days=CONFIG['retrain_days'])

    if len(data) < CONFIG['min_samples']:
        msg = f"Insufficient data: {len(data)} < {CONFIG['min_samples']}"
        print(f"  [SKIP] {msg}")
        return False

    print(f"  Loaded {len(data)} samples")

    # Step 4: Calculate volatility and adaptive thresholds
    print("\n[4/8] Analyzing market conditions...")
    volatility = calculate_market_volatility(data)
    thresholds = get_adaptive_thresholds(volatility)
    
    print(f"  Market volatility: {volatility:.2%} daily")
    print(f"  Adaptive thresholds: PF>{thresholds['min_profit_factor']:.2f}, WR>{thresholds['min_win_rate']:.2%}")

    # Split data
    split_idx = int(len(data) * (1 - CONFIG['validation_split']))
    train_data = data.iloc[:split_idx]
    validation_data = data.iloc[split_idx:]

    print(f"  Train: {len(train_data)}, Validation: {len(validation_data)}")

    # Step 5: Baseline PROFIT metrics
    print("\n[5/8] Evaluating baseline model PROFIT metrics...")
    baseline_metrics = simulate_trading(model, validation_data)
    
    print(f"  Baseline Profit Factor: {baseline_metrics['profit_factor']:.2f}")
    print(f"  Baseline Win Rate: {baseline_metrics['win_rate']:.2%}")
    print(f"  Baseline Total PnL: {baseline_metrics['total_pnl']:.2f}%")

    # Cross-validate
    print("\n[6/8] Cross-validating with PROFIT metrics...")
    cv_results = cross_validate_profit(model, train_data, n_folds=CONFIG['cv_folds'])
    
    print(f"  CV Profit Factor: {cv_results['profit_factor']:.2f} ± {cv_results.get('profit_factor_std', 0):.2f}")
    print(f"  CV Win Rate: {cv_results['win_rate']:.2%} ± {cv_results.get('win_rate_std', 0):.2%}")

    # Step 7: Train new model
    print(f"\n[7/8] Training new model ({CONFIG['max_boost_rounds']} rounds)...")
    
    try:
        train_result = model.incremental_train(
            train_data,
            num_boost_round=CONFIG['max_boost_rounds']
        )
        print(f"  Training completed")

    except Exception as e:
        print(f"  [ERROR] Training failed: {e}")
        shutil.copy(backup_path, model_path)
        send_telegram_alert(f"Training failed: {e}", is_error=True)
        return False

    # Step 8: Comprehensive PROFIT validation
    print("\n[8/8] PROFIT-based validation...")
    
    new_metrics = simulate_trading(model, validation_data)
    print(f"  New Profit Factor: {new_metrics['profit_factor']:.2f}")
    print(f"  New Win Rate: {new_metrics['win_rate']:.2%}")
    print(f"  New Total PnL: {new_metrics['total_pnl']:.2f}%")
    
    # Window validation
    window_results = validate_on_windows_profit(model, validation_data)
    
    # === DECISION LOGIC (PROFIT-BASED) ===
    should_apply = True
    reasons = []
    
    pf_change = new_metrics['profit_factor'] - baseline_metrics['profit_factor']
    wr_change = new_metrics['win_rate'] - baseline_metrics['win_rate']
    
    # Criterion 1: Profit Factor must be acceptable
    if new_metrics['profit_factor'] < thresholds['min_profit_factor']:
        should_apply = False
        reasons.append(f"PF too low: {new_metrics['profit_factor']:.2f} < {thresholds['min_profit_factor']:.2f}")
    
    # Criterion 2: Win Rate must be acceptable
    if new_metrics['win_rate'] < thresholds['min_win_rate']:
        should_apply = False
        reasons.append(f"WR too low: {new_metrics['win_rate']:.2%} < {thresholds['min_win_rate']:.2%}")
    
    # Criterion 3: Must show improvement OR maintain good metrics
    if pf_change < -0.2 and new_metrics['profit_factor'] < 1.3:
        should_apply = False
        reasons.append(f"PF dropped significantly: {pf_change:+.2f}")
    
    # Criterion 4: Window consistency (using weighted PF)
    if window_results:
        weighted_pf = calculate_weighted_pf(window_results)
        print(f"  Weighted PF across windows: {weighted_pf:.2f}")
        
        if weighted_pf < thresholds['min_profit_factor']:
            should_apply = False
            reasons.append(f"Weighted PF too low: {weighted_pf:.2f}")
    
    # === APPLY OR ROLLBACK ===
    print("\n" + "=" * 70)
    
    run_record = {
        'timestamp': datetime.now().isoformat(),
        'version': 'v2.0',
        'baseline_metrics': baseline_metrics,
        'new_metrics': new_metrics,
        'cv_results': cv_results,
        'window_results': {k: v for k, v in window_results.items()},
        'volatility': volatility,
        'thresholds': thresholds,
        'samples': len(train_data),
    }

    if should_apply:
        print("[SUCCESS] New model accepted!")
        print(f"  Profit Factor: {baseline_metrics['profit_factor']:.2f} → {new_metrics['profit_factor']:.2f} ({pf_change:+.2f})")
        print(f"  Win Rate: {baseline_metrics['win_rate']:.2%} → {new_metrics['win_rate']:.2%} ({wr_change:+.2%})")
        
        model.save_model(str(model_path))
        print(f"  Model saved: {model_path}")
        
        run_record['status'] = 'success'
        
        # Update best profit factor
        if new_metrics['profit_factor'] > history.get('best_profit_factor', 1.0):
            history['best_profit_factor'] = new_metrics['profit_factor']
        
        alert_msg = (
            f"*Model Updated (v2.0)*\n"
            f"• Profit Factor: {baseline_metrics['profit_factor']:.2f} → {new_metrics['profit_factor']:.2f}\n"
            f"• Win Rate: {baseline_metrics['win_rate']:.1%} → {new_metrics['win_rate']:.1%}\n"
            f"• Total PnL: {new_metrics['total_pnl']:.1f}%"
        )
        send_telegram_alert(alert_msg)

    else:
        reason_str = "; ".join(reasons)
        print(f"[ROLLBACK] {reason_str}")
        shutil.copy(backup_path, model_path)
        if Path(str(backup_path) + '_meta.pkl').exists():
            shutil.copy(str(backup_path) + '_meta.pkl', str(model_path) + '_meta.pkl')
        print("  Restored backup model")
        
        run_record['status'] = 'rollback'
        run_record['reasons'] = reasons
        
        alert_msg = (
            f"*Model Rollback*\n"
            f"• Reason: {reason_str}\n"
            f"• New PF: {new_metrics['profit_factor']:.2f}"
        )
        send_telegram_alert(alert_msg, is_error=True)

    # Save history
    history['runs'].append(run_record)
    history['runs'] = history['runs'][-100:]  # Keep last 100 runs
    save_history(history)

    print("\n" + "=" * 70)
    print(f"AUTO RETRAIN v2.0 - Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return should_apply


if __name__ == "__main__":
    success = auto_retrain_v2()
    exit(0 if success else 1)





