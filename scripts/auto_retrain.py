"""
Automatic model retraining with ENHANCED overfitting protection.
Runs daily to adapt model to current market conditions.

Features:
- Rolling window data (7 days instead of 24h)
- Cross-validation for reliable accuracy estimation
- Drift detection to identify market regime changes
- Model versioning with metrics history
- Telegram alerts for important events
- Ensemble validation on multiple time windows
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
from utils.logger_config import setup_logging

logger = setup_logging()

# Configuration
CONFIG = {
    'model_path': 'models/lightgbm_latest.pkl',
    'backup_path': 'models/lightgbm_backup.pkl',
    'history_path': 'models/retrain_history.json',
    'versions_dir': 'models/versions',

    # Retraining settings - INCREASED for better generalization
    'retrain_days': 7,              # Use last 7 days of data (was 24 hours)
    'min_samples': 2000,            # Minimum samples required (increased)
    'max_boost_rounds': 100,        # Limit iterations to prevent overfitting

    # Overfitting protection - STRICTER thresholds
    'min_accuracy': 0.48,           # Minimum accuracy to accept new model
    'max_accuracy_drop': 0.08,      # Max allowed accuracy drop from baseline
    'validation_split': 0.3,        # 30% holdout for validation
    'cv_folds': 3,                  # Cross-validation folds

    # Drift detection
    'drift_threshold': 0.15,        # Max allowed feature distribution shift
    'max_accuracy_variance': 0.05,  # Max variance across CV folds

    # Ensemble validation windows (hours)
    'validation_windows': [6, 12, 24],

    # Coins to use for retraining
    'coins': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT',
              'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT'],

    # Telegram alerts (optional)
    'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
}


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


def load_recent_data(days: int = 7) -> pd.DataFrame:
    """Load recent OHLCV data for retraining."""
    exchange = ccxt.binance({'enableRateLimit': True})
    all_data = []

    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    for coin in CONFIG['coins']:
        try:
            ohlcv = exchange.fetch_ohlcv(coin, '15m', since=since, limit=1500)

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


def detect_drift(old_data: pd.DataFrame, new_data: pd.DataFrame) -> Tuple[bool, float]:
    """
    Detect distribution drift between old and new data.

    Uses simple statistical tests on key features.
    Returns (drift_detected, drift_score)
    """
    try:
        # Compare return distributions
        old_returns = old_data['close'].pct_change().dropna()
        new_returns = new_data['close'].pct_change().dropna()

        # KS statistic for distribution comparison
        from scipy import stats
        ks_stat, _ = stats.ks_2samp(old_returns, new_returns)

        # Compare volatility
        old_vol = old_returns.std()
        new_vol = new_returns.std()
        vol_change = abs(new_vol - old_vol) / (old_vol + 1e-10)

        # Combined drift score
        drift_score = (ks_stat + vol_change) / 2

        drift_detected = drift_score > CONFIG['drift_threshold']

        logger.info(f"Drift detection: KS={ks_stat:.4f}, Vol change={vol_change:.4f}, Score={drift_score:.4f}")

        return drift_detected, drift_score

    except Exception as e:
        logger.warning(f"Drift detection failed: {e}")
        return False, 0.0


def cross_validate(model: LightGBMSignalGenerator, data: pd.DataFrame, n_folds: int = 3) -> Tuple[float, float]:
    """
    Perform time-series cross-validation.

    Returns (mean_accuracy, accuracy_std)
    """
    fold_size = len(data) // (n_folds + 1)
    accuracies = []

    for i in range(n_folds):
        # Time-series split: train on past, validate on future
        train_end = fold_size * (i + 1)
        val_end = fold_size * (i + 2)

        train_data = data.iloc[:train_end]
        val_data = data.iloc[train_end:val_end]

        if len(train_data) < 500 or len(val_data) < 100:
            continue

        try:
            # Create temporary model for this fold
            temp_model = LightGBMSignalGenerator()
            temp_model.train(train_data, num_boost_round=50, use_new_features=True)

            # Validate
            accuracy = validate_model(temp_model, val_data)
            accuracies.append(accuracy)
            logger.info(f"CV Fold {i+1}: accuracy={accuracy:.4f}")

        except Exception as e:
            logger.warning(f"CV Fold {i+1} failed: {e}")

    if not accuracies:
        return 0.0, 1.0

    mean_acc = np.mean(accuracies)
    std_acc = np.std(accuracies)

    return mean_acc, std_acc


def validate_on_windows(model: LightGBMSignalGenerator, data: pd.DataFrame) -> Dict[str, float]:
    """
    Validate model on multiple time windows for ensemble validation.
    """
    results = {}
    now = data.index.max() if hasattr(data.index, 'max') else datetime.now()

    for hours in CONFIG['validation_windows']:
        try:
            # Get data for this window
            window_start = now - timedelta(hours=hours)
            if hasattr(data.index, 'max'):
                window_data = data[data.index >= window_start]
            else:
                window_data = data.tail(int(hours * 4))  # Approximate for 15m candles

            if len(window_data) < 50:
                continue

            accuracy = validate_model(model, window_data)
            results[f'{hours}h'] = accuracy
            logger.info(f"Window {hours}h: accuracy={accuracy:.4f}")

        except Exception as e:
            logger.warning(f"Window {hours}h validation failed: {e}")

    return results


def validate_model(model: LightGBMSignalGenerator, validation_data: pd.DataFrame) -> float:
    """Validate model on holdout data and return accuracy."""
    try:
        predictions = model.predict_batch(validation_data)

        # Create labels for validation
        returns = validation_data['close'].pct_change().shift(-1)
        labels = np.where(returns > 0.005, 2, np.where(returns < -0.005, 0, 1))

        # Calculate accuracy (simplified)
        min_len = min(len(predictions), len(labels))
        if min_len == 0:
            return 0.0

        accuracy = np.mean(predictions[:min_len] == labels[:min_len])

        return float(accuracy)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 0.0


def load_history() -> dict:
    """Load retraining history."""
    history_path = Path(CONFIG['history_path'])
    if history_path.exists():
        with open(history_path, 'r') as f:
            return json.load(f)
    return {'runs': [], 'baseline_accuracy': 0.5, 'best_accuracy': 0.5}


def save_history(history: dict):
    """Save retraining history."""
    with open(CONFIG['history_path'], 'w') as f:
        json.dump(history, f, indent=2, default=str)


def save_model_version(model: LightGBMSignalGenerator, metrics: Dict):
    """Save model version with timestamp and metrics."""
    versions_dir = Path(CONFIG['versions_dir'])
    versions_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    version_path = versions_dir / f'lightgbm_{timestamp}.pkl'

    model.save_model(str(version_path))

    # Save metrics
    metrics_path = versions_dir / f'metrics_{timestamp}.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)

    logger.info(f"Saved model version: {version_path}")

    # Cleanup old versions (keep last 10)
    versions = sorted(versions_dir.glob('lightgbm_*.pkl'))
    if len(versions) > 10:
        for old_version in versions[:-10]:
            old_version.unlink()
            # Also delete metrics file
            old_metrics = str(old_version).replace('lightgbm_', 'metrics_').replace('.pkl', '.json')
            Path(old_metrics).unlink(missing_ok=True)


def auto_retrain():
    """
    Main auto-retraining function with ENHANCED overfitting protection.

    Protections:
    1. Cross-validation for reliable accuracy estimation
    2. Multi-window validation for temporal robustness
    3. Drift detection to identify market regime changes
    4. Model versioning for rollback capability
    5. Telegram alerts for monitoring
    6. Stricter thresholds and more data
    """
    print("=" * 60)
    print("AUTO RETRAIN (Enhanced) - Started at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    history = load_history()
    model_path = Path(CONFIG['model_path'])
    backup_path = Path(CONFIG['backup_path'])

    # Step 1: Load current model
    if not model_path.exists():
        print("[ERROR] No model found. Please train base model first.")
        send_telegram_alert("No base model found for retraining!", is_error=True)
        return False

    print("\n[1/7] Loading current model...")
    model = LightGBMSignalGenerator(model_path=str(model_path))

    # Step 2: Create backup
    print("[2/7] Creating backup...")
    shutil.copy(model_path, backup_path)
    meta_path = str(model_path) + '_meta.pkl'
    if Path(meta_path).exists():
        shutil.copy(meta_path, str(backup_path) + '_meta.pkl')
    print(f"  Backup saved: {backup_path}")

    # Step 3: Load recent data (7 days)
    print(f"\n[3/7] Loading last {CONFIG['retrain_days']} days of data...")
    data = load_recent_data(days=CONFIG['retrain_days'])

    if len(data) < CONFIG['min_samples']:
        msg = f"Insufficient data: {len(data)} < {CONFIG['min_samples']} required"
        print(f"  [SKIP] {msg}")
        return False

    print(f"  Loaded {len(data)} samples")

    # Split for validation (time-series split)
    split_idx = int(len(data) * (1 - CONFIG['validation_split']))
    train_data = data.iloc[:split_idx]
    validation_data = data.iloc[split_idx:]

    print(f"  Train: {len(train_data)}, Validation: {len(validation_data)}")

    # Step 4: Drift detection
    print("\n[4/7] Checking for data drift...")
    if len(train_data) > 1000:
        old_data = train_data.iloc[:len(train_data)//2]
        new_data = train_data.iloc[len(train_data)//2:]
        drift_detected, drift_score = detect_drift(old_data, new_data)

        if drift_detected:
            print(f"  ⚠️  Significant drift detected (score={drift_score:.4f})")
            print("  Consider full retraining instead of incremental")
        else:
            print(f"  ✓ No significant drift (score={drift_score:.4f})")

    # Step 5: Validate baseline with cross-validation
    print("\n[5/7] Cross-validating baseline model...")
    cv_mean, cv_std = cross_validate(model, train_data, n_folds=CONFIG['cv_folds'])
    print(f"  CV Accuracy: {cv_mean:.4f} ± {cv_std:.4f}")

    if cv_std > CONFIG['max_accuracy_variance']:
        print(f"  ⚠️  High variance in CV - model may be unstable")

    baseline_accuracy = validate_model(model, validation_data)
    print(f"  Holdout accuracy: {baseline_accuracy:.4f}")

    # Update best accuracy in history
    if baseline_accuracy > history.get('best_accuracy', 0.5):
        history['best_accuracy'] = baseline_accuracy

    # Step 6: Incremental training
    print(f"\n[6/7] Incremental training ({CONFIG['max_boost_rounds']} rounds)...")

    try:
        metrics = model.incremental_train(
            train_data,
            num_boost_round=CONFIG['max_boost_rounds']
        )
        print(f"  Training accuracy: {metrics['accuracy']:.4f}")

    except Exception as e:
        print(f"  [ERROR] Training failed: {e}")
        print("  Rolling back to backup...")
        shutil.copy(backup_path, model_path)
        send_telegram_alert(f"Training failed: {e}", is_error=True)
        return False

    # Step 7: Comprehensive validation
    print("\n[7/7] Comprehensive validation...")

    # Holdout validation
    new_accuracy = validate_model(model, validation_data)
    print(f"  New holdout accuracy: {new_accuracy:.4f}")

    accuracy_change = new_accuracy - baseline_accuracy
    print(f"  Accuracy change: {accuracy_change:+.4f}")

    # Multi-window validation
    window_results = validate_on_windows(model, validation_data)

    # Check overfitting protection criteria
    should_apply = True
    reasons = []

    # Criterion 1: Minimum accuracy
    if new_accuracy < CONFIG['min_accuracy']:
        should_apply = False
        reasons.append(f"Accuracy too low: {new_accuracy:.4f} < {CONFIG['min_accuracy']:.4f}")

    # Criterion 2: Max accuracy drop
    if accuracy_change < -CONFIG['max_accuracy_drop']:
        should_apply = False
        reasons.append(f"Accuracy dropped: {accuracy_change:+.4f}")

    # Criterion 3: Multi-window consistency
    if window_results:
        window_accs = list(window_results.values())
        if np.std(window_accs) > 0.1:
            should_apply = False
            reasons.append(f"Inconsistent across windows: std={np.std(window_accs):.4f}")

    # Apply or rollback
    print("\n" + "=" * 60)

    run_record = {
        'timestamp': datetime.now().isoformat(),
        'baseline_accuracy': baseline_accuracy,
        'new_accuracy': new_accuracy,
        'accuracy_change': accuracy_change,
        'cv_mean': cv_mean,
        'cv_std': cv_std,
        'window_results': window_results,
        'samples': len(train_data),
    }

    if should_apply:
        print("[SUCCESS] New model accepted!")
        model.save_model(str(model_path))
        save_model_version(model, run_record)
        print(f"  Model saved: {model_path}")

        run_record['status'] = 'success'

        # Send success alert
        alert_msg = (
            f"*Model Updated Successfully*\n"
            f"• Accuracy: {baseline_accuracy:.2%} → {new_accuracy:.2%}\n"
            f"• Change: {accuracy_change:+.2%}\n"
            f"• Samples: {len(train_data)}"
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

        # Send rollback alert
        alert_msg = (
            f"*Model Rollback*\n"
            f"• Reason: {reason_str}\n"
            f"• Accuracy: {new_accuracy:.2%}"
        )
        send_telegram_alert(alert_msg, is_error=True)

    # Save history
    history['runs'].append(run_record)
    history['runs'] = history['runs'][-50:]  # Keep last 50 runs
    save_history(history)

    print("\n" + "=" * 60)
    print("AUTO RETRAIN - Completed at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    return should_apply


if __name__ == "__main__":
    success = auto_retrain()
    exit(0 if success else 1)
