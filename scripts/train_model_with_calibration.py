"""
Enhanced Model Training with Confusion Matrix Calibration

Обучает модель на историческом датасете с калибровкой вероятностей через confusion matrix.
Интегрируется с EnhancedSignalGenerator для согласованного качества сигналов.

Key features:
- Historical data training (365+ days)
- Confusion matrix calibration (Platt scaling + Isotonic regression)
- Quality metrics: Accuracy, Precision, Recall, F1, Profit Factor
- Integration with EnhancedSignalGenerator for signal consistency
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import ccxt
from collections import Counter

try:
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        confusion_matrix, classification_report, 
        accuracy_score, precision_recall_fscore_support,
        log_loss
    )
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("WARNING: sklearn not available. Calibration disabled.")

from ml.lightgbm_model import LightGBMSignalGenerator
from utils.logger_config import setup_logging
from utils.enhanced_signal_generator import EnhancedSignalGenerator

logger = setup_logging()

# Configuration
CONFIG = {
    'model_path': 'models/lightgbm_calibrated.pkl',
    'calibration_path': 'models/calibration_meta.pkl',
    'history_path': 'models/training_history.json',
    
    # Training settings
    'training_days': 365,        # 1 year of data
    'min_samples': 10000,        # Minimum samples
    'test_split': 0.2,           # 20% for testing
    'calibration_split': 0.2,    # 20% for calibration (from test)
    'timeframe': '15m',
    
    # Model parameters
    'num_boost_round': 500,
    'early_stopping_rounds': 50,
    'calibration_method': 'isotonic',  # 'isotonic' or 'sigmoid'
    
    # Top 50 coins for training
    'coins': [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
        'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT',
        'LINK/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'NEAR/USDT',
        'ALGO/USDT', 'FTM/USDT', 'ICP/USDT', 'APT/USDT', 'ARB/USDT',
        'OP/USDT', 'INJ/USDT', 'TIA/USDT', 'SEI/USDT', 'SUI/USDT',
        'IMX/USDT', 'SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'GALA/USDT',
        'SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT', 'BONK/USDT', 'WIF/USDT',
        'FET/USDT', 'RNDR/USDT', 'TAO/USDT', 'ARKM/USDT', 'OCEAN/USDT',
        'CRO/USDT', 'OKB/USDT', 'MKR/USDT', 'AAVE/USDT', 'SNX/USDT',
        'FIL/USDT', 'AR/USDT', 'GRT/USDT', 'ENJ/USDT', 'CHZ/USDT',
    ],
}


def prepare_training_labels(df: pd.DataFrame, forward_periods: int = 8, threshold: float = 0.005) -> pd.Series:
    """
    Create training labels based on future price movement.
    
    Args:
        df: OHLCV DataFrame
        forward_periods: Periods to look ahead (8 periods = 2h on 15m)
        threshold: Price change threshold (0.5%)
    
    Returns:
        Series with labels (0=SELL, 1=HOLD, 2=BUY)
    """
    future_returns = df["close"].shift(-forward_periods) / df["close"] - 1
    
    labels = pd.Series(1, index=df.index)  # Default: HOLD
    
    # BUY signal if price goes up > threshold
    labels[future_returns > threshold] = 2
    
    # SELL signal if price goes down > threshold
    labels[future_returns < -threshold] = 0
    
    return labels


def load_historical_data(days: int = 365) -> pd.DataFrame:
    """Load historical OHLCV data for training."""
    exchange = ccxt.binance({'enableRateLimit': True})
    all_data = []
    
    logger.info(f"Loading {days} days of historical data for {len(CONFIG['coins'])} coins...")
    
    # Calculate since timestamp
    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    # Binance allows max 1000 candles per request
    # For 15m: 1000 candles = ~10 days
    # Need multiple requests for longer periods
    requests_per_coin = max(1, (days // 10) + 1)
    
    for i, coin in enumerate(CONFIG['coins'], 1):
        try:
            logger.info(f"[{i}/{len(CONFIG['coins'])}] Loading {coin}...")
            
            coin_data = []
            current_since = since
            
            for req in range(requests_per_coin):
                ohlcv = exchange.fetch_ohlcv(
                    coin, 
                    CONFIG['timeframe'], 
                    since=current_since, 
                    limit=1000
                )
                
                if not ohlcv:
                    break
                
                df_chunk = pd.DataFrame(
                    ohlcv, 
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df_chunk['timestamp'] = pd.to_datetime(df_chunk['timestamp'], unit='ms')
                df_chunk.set_index('timestamp', inplace=True)
                df_chunk['symbol'] = coin
                
                coin_data.append(df_chunk)
                
                # Update since for next request
                if len(ohlcv) < 1000:
                    break
                current_since = int(df_chunk.index[-1].timestamp() * 1000) + 1
            
            if coin_data:
                coin_df = pd.concat(coin_data, ignore_index=False)
                coin_df = coin_df[~coin_df.index.duplicated(keep='first')]
                coin_df.sort_index(inplace=True)
                all_data.append(coin_df)
                logger.info(f"  ✓ Loaded {len(coin_df)} candles for {coin}")
            else:
                logger.warning(f"  ✗ No data for {coin}")
        
        except Exception as e:
            logger.warning(f"  ✗ Failed to load {coin}: {e}")
    
    if not all_data:
        logger.error("No data loaded! Exiting.")
        return pd.DataFrame()
    
    combined = pd.concat(all_data, ignore_index=False)
    combined = combined[~combined.index.duplicated(keep='first')]
    combined.sort_index(inplace=True)
    
    logger.info(f"Total samples loaded: {len(combined)} candles")
    return combined


def calculate_confusion_matrix_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
    """
    Calculate comprehensive metrics from confusion matrix.
    
    Returns:
        Dictionary with accuracy, precision, recall, F1, confusion matrix
    """
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    
    # Calculate per-class metrics
    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2], zero_division=0
    )
    
    # Class names: SELL (0), HOLD (1), BUY (2)
    metrics = {
        'accuracy': float(accuracy),
        'confusion_matrix': cm.tolist(),
        'classes': ['SELL', 'HOLD', 'BUY'],
        'precision': {
            'SELL': float(precision[0]),
            'HOLD': float(precision[1]),
            'BUY': float(precision[2]),
            'macro_avg': float(np.mean(precision)),
        },
        'recall': {
            'SELL': float(recall[0]),
            'HOLD': float(recall[1]),
            'BUY': float(recall[2]),
            'macro_avg': float(np.mean(recall)),
        },
        'f1': {
            'SELL': float(f1[0]),
            'HOLD': float(f1[1]),
            'BUY': float(f1[2]),
            'macro_avg': float(np.mean(f1)),
        },
        'support': {
            'SELL': int(support[0]),
            'HOLD': int(support[1]),
            'BUY': int(support[2]),
        },
    }
    
    return metrics


def apply_calibration(
    model: LightGBMSignalGenerator,
    X_cal: np.ndarray,
    y_cal: np.ndarray,
    method: str = 'isotonic'
) -> Dict:
    """
    Apply probability calibration using confusion matrix insights.
    
    Args:
        model: Trained LightGBM model
        X_cal: Calibration features
        y_cal: True labels for calibration
        method: 'isotonic' or 'sigmoid'
    
    Returns:
        Dictionary with calibration parameters and metrics
    """
    if not HAS_SKLEARN:
        logger.warning("sklearn not available, skipping calibration")
        return {}
    
    # Get raw predictions (probabilities)
    probs = model.model.predict(X_cal)
    
    # Convert to class predictions
    pred_classes = np.argmax(probs, axis=1)
    
    # Calculate confusion matrix metrics before calibration
    metrics_before = calculate_confusion_matrix_metrics(y_cal, pred_classes)
    
    logger.info("Applying probability calibration...")
    logger.info(f"  Method: {method}")
    logger.info(f"  Calibration samples: {len(X_cal)}")
    
    # Apply calibration per class using Isotonic Regression
    calibration_params = {}
    
    if method == 'isotonic':
        for class_idx, class_name in enumerate(['SELL', 'HOLD', 'BUY']):
            # Get probabilities for this class
            class_probs = probs[:, class_idx]
            # Binary labels: 1 if true class, 0 otherwise
            class_labels = (y_cal == class_idx).astype(int)
            
            # Fit isotonic regression
            calibrator = IsotonicRegression(out_of_bounds='clip')
            calibrator.fit(class_probs, class_labels)
            
            calibration_params[class_name] = calibrator
            
            logger.info(f"  Calibrated {class_name}: {len(calibrator.X_thresholds_)} bins")
    
    # Apply calibration to predictions
    calibrated_probs = np.zeros_like(probs)
    for class_idx, class_name in enumerate(['SELL', 'HOLD', 'BUY']):
        if class_name in calibration_params:
            calibrated_probs[:, class_idx] = calibration_params[class_name].transform(probs[:, class_idx])
        else:
            calibrated_probs[:, class_idx] = probs[:, class_idx]
    
    # Renormalize probabilities
    calibrated_probs = calibrated_probs / calibrated_probs.sum(axis=1, keepdims=True)
    
    # Convert to class predictions
    calibrated_pred_classes = np.argmax(calibrated_probs, axis=1)
    
    # Calculate metrics after calibration
    metrics_after = calculate_confusion_matrix_metrics(y_cal, calibrated_pred_classes)
    
    # Calculate log loss improvement
    log_loss_before = log_loss(y_cal, probs, labels=[0, 1, 2])
    log_loss_after = log_loss(y_cal, calibrated_probs, labels=[0, 1, 2])
    
    logger.info(f"  Log Loss: {log_loss_before:.4f} → {log_loss_after:.4f} ({log_loss_before - log_loss_after:+.4f})")
    logger.info(f"  Accuracy: {metrics_before['accuracy']:.4f} → {metrics_after['accuracy']:.4f} ({metrics_after['accuracy'] - metrics_before['accuracy']:+.4f})")
    
    return {
        'calibration_params': calibration_params,
        'method': method,
        'metrics_before': metrics_before,
        'metrics_after': metrics_after,
        'log_loss_before': float(log_loss_before),
        'log_loss_after': float(log_loss_after),
        'improvement': float(log_loss_before - log_loss_after),
    }


def integrate_with_enhanced_generator(
    ml_prediction: Dict,
    enhanced_signal: Tuple[str, int, List[str]],
    symbol: str,
    ticker: Dict,
    ohlcv_df: pd.DataFrame
) -> Dict:
    """
    Интегрирует ML предсказания с EnhancedSignalGenerator для согласованности.
    
    Args:
        ml_prediction: ML prediction dict {'action': 'BUY', 'confidence': 0.75, 'probabilities': {...}}
        enhanced_signal: Tuple from EnhancedSignalGenerator (signal, confidence, reasons)
        symbol: Trading pair
        ticker: Ticker data
        ohlcv_df: OHLCV DataFrame
    
    Returns:
        Integrated signal dictionary
    """
    ml_action = ml_prediction.get('action', 'HOLD')
    ml_confidence = ml_prediction.get('confidence', 0.5)
    ml_probs = ml_prediction.get('probabilities', {})
    
    enh_signal, enh_confidence, enh_reasons = enhanced_signal
    
    # Веса для комбинирования
    ML_WEIGHT = 0.4  # 40% ML
    ENHANCED_WEIGHT = 0.6  # 60% Rule-based (более надежный)
    
    # Согласованность сигналов
    if ml_action == enh_signal:
        # Согласованы - повышаем confidence
        combined_confidence = (
            ml_confidence * ML_WEIGHT + 
            (enh_confidence / 100.0) * ENHANCED_WEIGHT
        ) * 1.1  # +10% за согласованность
        combined_confidence = min(1.0, combined_confidence)
        
        integrated_signal = {
            'signal': ml_action,
            'confidence': combined_confidence,
            'method': 'integrated_agreement',
            'ml_contribution': ml_confidence * ML_WEIGHT,
            'enhanced_contribution': (enh_confidence / 100.0) * ENHANCED_WEIGHT,
            'reasons': enh_reasons + [f"ML подтверждает: {ml_action} ({ml_confidence:.0%})"],
        }
    else:
        # Не согласованы - используем правило большинства
        if enh_confidence > 60:  # Высокая уверенность в rule-based
            integrated_signal = {
                'signal': enh_signal,
                'confidence': (enh_confidence / 100.0) * 0.9,  # Снижаем немного
                'method': 'enhanced_priority',
                'ml_disagreement': ml_action,
                'ml_confidence': ml_confidence,
                'reasons': enh_reasons + [f"⚠️ ML предлагает {ml_action}, но правило предпочтительнее"],
            }
        elif ml_confidence > 0.7:  # Высокая уверенность в ML
            integrated_signal = {
                'signal': ml_action,
                'confidence': ml_confidence * 0.9,  # Снижаем немного
                'method': 'ml_priority',
                'enhanced_disagreement': enh_signal,
                'enhanced_confidence': enh_confidence,
                'reasons': enh_reasons + [f"⚠️ Правило предлагает {enh_signal}, но ML предпочтительнее"],
            }
        else:
            # Низкая уверенность в обоих - HOLD
            integrated_signal = {
                'signal': 'HOLD',
                'confidence': 0.5,
                'method': 'uncertain',
                'ml_signal': ml_action,
                'enhanced_signal': enh_signal,
                'reasons': enh_reasons + ["⚠️ Противоречие между ML и правилом, HOLD"],
            }
    
    return integrated_signal


def train_with_calibration():
    """
    Main training function with confusion matrix calibration.
    """
    print("=" * 80)
    print("ENHANCED MODEL TRAINING WITH CALIBRATION")
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Step 1: Load historical data
    print(f"\n[1/6] Loading {CONFIG['training_days']} days of historical data...")
    data = load_historical_data(days=CONFIG['training_days'])
    
    if len(data) < CONFIG['min_samples']:
        logger.error(f"Insufficient data: {len(data)} < {CONFIG['min_samples']}")
        return False
    
    print(f"  ✓ Loaded {len(data):,} samples")
    
    # Step 2: Prepare labels
    print("\n[2/6] Preparing training labels...")
    data['label'] = prepare_training_labels(data, forward_periods=8, threshold=0.005)
    
    # Remove rows with NaN labels (last forward_periods rows)
    data = data.dropna(subset=['label'])
    data['label'] = data['label'].astype(int)
    
    label_counts = data['label'].value_counts().sort_index()
    print(f"  Label distribution:")
    print(f"    SELL (0): {label_counts.get(0, 0):,} ({label_counts.get(0, 0)/len(data)*100:.1f}%)")
    print(f"    HOLD (1): {label_counts.get(1, 0):,} ({label_counts.get(1, 0)/len(data)*100:.1f}%)")
    print(f"    BUY (2):  {label_counts.get(2, 0):,} ({label_counts.get(2, 0)/len(data)*100:.1f}%)")
    
    # Step 3: Prepare features
    print("\n[3/6] Preparing features...")
    model = LightGBMSignalGenerator()
    
    # Split data chronologically
    split_idx = int(len(data) * (1 - CONFIG['test_split']))
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]
    
    # Further split test for calibration
    cal_split_idx = int(len(test_data) * (1 - CONFIG['calibration_split']))
    val_data = test_data.iloc[:cal_split_idx]
    cal_data = test_data.iloc[cal_split_idx:]
    
    print(f"  Train: {len(train_data):,} samples")
    print(f"  Validation: {len(val_data):,} samples")
    print(f"  Calibration: {len(cal_data):,} samples")
    
    # Train model
    print(f"\n[4/6] Training LightGBM model ({CONFIG['num_boost_round']} rounds)...")
    train_metrics = model.train(
        df=train_data,
        num_boost_round=CONFIG['num_boost_round'],
        early_stopping_rounds=CONFIG['early_stopping_rounds'],
        test_size=0.2,
        use_new_features=True,
    )
    
    print(f"  ✓ Training completed")
    print(f"    Training accuracy: {train_metrics.get('train_accuracy', 0):.4f}")
    print(f"    Validation accuracy: {train_metrics.get('val_accuracy', 0):.4f}")
    
    # Step 5: Evaluate on validation set
    print("\n[5/6] Evaluating model...")
    
    # Prepare validation features
    X_val, _ = model._prepare_features(val_data)
    y_val = val_data['label'].values
    
    # Predictions
    X_val_scaled = model.scaler.transform(X_val)
    val_probs = model.model.predict(X_val_scaled)
    val_preds = np.argmax(val_probs, axis=1)
    
    # Calculate metrics
    val_metrics = calculate_confusion_matrix_metrics(y_val, val_preds)
    
    print(f"  Validation Accuracy: {val_metrics['accuracy']:.4f}")
    print(f"  Precision: SELL={val_metrics['precision']['SELL']:.3f}, "
          f"HOLD={val_metrics['precision']['HOLD']:.3f}, "
          f"BUY={val_metrics['precision']['BUY']:.3f}")
    print(f"  Recall: SELL={val_metrics['recall']['SELL']:.3f}, "
          f"HOLD={val_metrics['recall']['HOLD']:.3f}, "
          f"BUY={val_metrics['recall']['BUY']:.3f}")
    
    # Step 6: Apply calibration
    print(f"\n[6/6] Applying {CONFIG['calibration_method']} calibration...")
    
    X_cal, _ = model._prepare_features(cal_data)
    y_cal = cal_data['label'].values
    X_cal_scaled = model.scaler.transform(X_cal)
    
    calibration_result = apply_calibration(
        model=model,
        X_cal=X_cal_scaled,
        y_cal=y_cal,
        method=CONFIG['calibration_method']
    )
    
    # Save model and calibration
    model_path = Path(CONFIG['model_path'])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    model.save_model(str(model_path))
    
    # Save calibration metadata
    if calibration_result and calibration_result.get('calibration_params'):
        cal_path = Path(CONFIG['calibration_path'])
        cal_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cal_path, 'wb') as f:
            pickle.dump(calibration_result['calibration_params'], f)
        print(f"  ✓ Calibration saved to {cal_path}")
    
    # Save training history
    history = {
        'timestamp': datetime.now().isoformat(),
        'training_samples': len(train_data),
        'validation_samples': len(val_data),
        'calibration_samples': len(cal_data),
        'training_metrics': train_metrics,
        'validation_metrics': val_metrics,
        'calibration_result': {
            k: v for k, v in calibration_result.items() 
            if k != 'calibration_params'  # Don't serialize calibrators
        },
        'config': CONFIG,
    }
    
    history_path = Path(CONFIG['history_path'])
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2, default=str)
    
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE!")
    print("=" * 80)
    print(f"Model saved: {model_path}")
    print(f"Calibration saved: {CONFIG['calibration_path']}")
    print(f"History saved: {history_path}")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train LightGBM model with calibration")
    parser.add_argument("--days", type=int, default=365, help="Training days (default: 365)")
    parser.add_argument("--timeframe", default="15m", help="Timeframe (default: 15m)")
    parser.add_argument("--output", default="models/lightgbm_calibrated.pkl", help="Model save path")
    parser.add_argument("--calibration", default="isotonic", choices=['isotonic', 'sigmoid'], 
                       help="Calibration method (default: isotonic)")
    
    args = parser.parse_args()
    
    # Update config with arguments
    CONFIG['training_days'] = args.days
    CONFIG['timeframe'] = args.timeframe
    CONFIG['model_path'] = args.output
    CONFIG['calibration_path'] = args.output.replace('.pkl', '_calibration.pkl')
    CONFIG['calibration_method'] = args.calibration
    
    success = train_with_calibration()
    exit(0 if success else 1)

