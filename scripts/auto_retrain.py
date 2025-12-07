"""
Automatic model retraining with overfitting protection.
Runs daily to adapt model to current market conditions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import shutil
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import ccxt
from ml.lightgbm_model import LightGBMSignalGenerator
from utils.logger_config import setup_logging

logger = setup_logging()

# Configuration
CONFIG = {
    'model_path': 'models/lightgbm_latest.pkl',
    'backup_path': 'models/lightgbm_backup.pkl',
    'history_path': 'models/retrain_history.json',

    # Retraining settings
    'retrain_hours': 24,           # Use last 24 hours of data
    'min_samples': 500,            # Minimum samples required
    'max_boost_rounds': 50,        # Limit iterations to prevent overfitting

    # Overfitting protection
    'min_accuracy': 0.45,          # Minimum accuracy to accept new model
    'max_accuracy_drop': 0.10,     # Max allowed accuracy drop from baseline
    'validation_split': 0.3,       # 30% holdout for validation

    # Coins to use for retraining
    'coins': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT'],
}


def load_recent_data(hours: int = 24) -> pd.DataFrame:
    """Load recent OHLCV data for retraining."""
    exchange = ccxt.binance({'enableRateLimit': True})
    all_data = []

    for coin in CONFIG['coins']:
        try:
            since = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(coin, '15m', since=since, limit=1000)

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

    return pd.concat(all_data, ignore_index=True)


def validate_model(model: LightGBMSignalGenerator, validation_data: pd.DataFrame) -> float:
    """Validate model on holdout data and return accuracy."""
    try:
        predictions = model.predict_batch(validation_data)

        # Create labels for validation
        returns = validation_data['close'].pct_change().shift(-1)
        labels = np.where(returns > 0.005, 2, np.where(returns < -0.005, 0, 1))

        # Calculate accuracy (simplified)
        min_len = min(len(predictions), len(labels))
        accuracy = np.mean(predictions[:min_len] == labels[:min_len])

        return accuracy
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 0.0


def load_history() -> dict:
    """Load retraining history."""
    history_path = Path(CONFIG['history_path'])
    if history_path.exists():
        with open(history_path, 'r') as f:
            return json.load(f)
    return {'runs': [], 'baseline_accuracy': 0.5}


def save_history(history: dict):
    """Save retraining history."""
    with open(CONFIG['history_path'], 'w') as f:
        json.dump(history, f, indent=2, default=str)


def auto_retrain():
    """
    Main auto-retraining function with overfitting protection.

    Protections:
    1. Validates new model on holdout data before applying
    2. Rolls back if accuracy drops too much
    3. Limits boost rounds to prevent overfitting
    4. Requires minimum data samples
    5. Logs all metrics for monitoring
    """
    print("=" * 60)
    print("AUTO RETRAIN - Started at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    history = load_history()
    model_path = Path(CONFIG['model_path'])
    backup_path = Path(CONFIG['backup_path'])

    # Step 1: Load current model
    if not model_path.exists():
        print("[ERROR] No model found. Please train base model first.")
        return False

    print("\n[1/5] Loading current model...")
    model = LightGBMSignalGenerator(model_path=str(model_path))

    # Step 2: Create backup
    print("[2/5] Creating backup...")
    shutil.copy(model_path, backup_path)
    meta_path = str(model_path) + '_meta.pkl'
    if Path(meta_path).exists():
        shutil.copy(meta_path, str(backup_path) + '_meta.pkl')
    print(f"  Backup saved: {backup_path}")

    # Step 3: Load recent data
    print(f"\n[3/5] Loading last {CONFIG['retrain_hours']} hours of data...")
    data = load_recent_data(hours=CONFIG['retrain_hours'])

    if len(data) < CONFIG['min_samples']:
        print(f"  [SKIP] Insufficient data: {len(data)} < {CONFIG['min_samples']} required")
        return False

    print(f"  Loaded {len(data)} samples")

    # Split for validation
    split_idx = int(len(data) * (1 - CONFIG['validation_split']))
    train_data = data.iloc[:split_idx]
    validation_data = data.iloc[split_idx:]

    print(f"  Train: {len(train_data)}, Validation: {len(validation_data)}")

    # Step 4: Validate baseline
    print("\n[4/5] Checking baseline accuracy...")
    baseline_accuracy = validate_model(model, validation_data)
    print(f"  Baseline accuracy: {baseline_accuracy:.2%}")

    if baseline_accuracy > history['baseline_accuracy']:
        history['baseline_accuracy'] = baseline_accuracy

    # Step 5: Incremental training
    print(f"\n[5/5] Incremental training ({CONFIG['max_boost_rounds']} rounds)...")

    try:
        metrics = model.incremental_train(
            train_data,
            num_boost_round=CONFIG['max_boost_rounds']
        )
        print(f"  Training accuracy: {metrics['accuracy']:.2%}")

    except Exception as e:
        print(f"  [ERROR] Training failed: {e}")
        print("  Rolling back to backup...")
        shutil.copy(backup_path, model_path)
        return False

    # Validate new model
    new_accuracy = validate_model(model, validation_data)
    print(f"  New validation accuracy: {new_accuracy:.2%}")

    accuracy_change = new_accuracy - baseline_accuracy
    print(f"  Accuracy change: {accuracy_change:+.2%}")

    # Check overfitting protection
    should_apply = True
    reason = ""

    if new_accuracy < CONFIG['min_accuracy']:
        should_apply = False
        reason = f"Accuracy too low: {new_accuracy:.2%} < {CONFIG['min_accuracy']:.2%}"

    elif accuracy_change < -CONFIG['max_accuracy_drop']:
        should_apply = False
        reason = f"Accuracy dropped too much: {accuracy_change:+.2%}"

    # Apply or rollback
    print("\n" + "=" * 60)

    if should_apply:
        print("[SUCCESS] New model accepted!")
        model.save_model(str(model_path))
        print(f"  Model saved: {model_path}")

        # Log success
        history['runs'].append({
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'baseline_accuracy': baseline_accuracy,
            'new_accuracy': new_accuracy,
            'accuracy_change': accuracy_change,
            'samples': len(train_data),
        })
    else:
        print(f"[ROLLBACK] {reason}")
        shutil.copy(backup_path, model_path)
        if Path(str(backup_path) + '_meta.pkl').exists():
            shutil.copy(str(backup_path) + '_meta.pkl', str(model_path) + '_meta.pkl')
        print("  Restored backup model")

        # Log failure
        history['runs'].append({
            'timestamp': datetime.now().isoformat(),
            'status': 'rollback',
            'reason': reason,
            'baseline_accuracy': baseline_accuracy,
            'new_accuracy': new_accuracy,
        })

    # Keep only last 30 runs
    history['runs'] = history['runs'][-30:]
    save_history(history)

    print("\n" + "=" * 60)
    print("AUTO RETRAIN - Completed at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    return should_apply


if __name__ == "__main__":
    success = auto_retrain()
    exit(0 if success else 1)
