"""
Comprehensive LightGBM training script for MaxFlash.
Trains model on historical data with barrier-based labels (TP before SL).

Key features:
- 1h timeframe for reduced noise and better signal quality
- Barrier-based labels (TP hit before SL within horizon)
- Top-20 coins by volume across Binance/Bybit/OKX
- Enhanced feature engineering
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import ccxt
from datetime import datetime, timedelta
from ml.lightgbm_model import LightGBMSignalGenerator
from ml.labeling import get_label_distribution
from utils.logger_config import setup_logging

logger = setup_logging()

# Training configuration
TRAINING_CONFIG = {
    'timeframe': '1h',           # 1h timeframe for reduced noise
    'days_back': 180,            # 6 months of data
    'min_candles': 500,          # Minimum candles required
    'use_barrier_labels': True,  # Use TP/SL barrier labels
    'tp_atr_mult': 2.5,          # TP = entry + 2.5*ATR
    'sl_atr_mult': 1.5,          # SL = entry - 1.5*ATR
    'horizon_bars': 4,           # Look 4 bars (4 hours) ahead
    'use_new_features': True,    # Enhanced feature engineering
}

# Top coins by market cap (excluding stablecoins)
# Will be overridden by dynamic top-20 selection if available
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

# Try to use dynamic universe selector
try:
    from utils.universe_selector import get_top_n_pairs
    HAS_UNIVERSE_SELECTOR = True
except ImportError:
    HAS_UNIVERSE_SELECTOR = False
    logger.warning("Universe selector not available, using static coin list")


def get_training_coins(n: int = 20) -> list:
    """
    Get list of coins to train on.
    
    Uses dynamic universe selector if available, falls back to static list.
    
    Args:
        n: Number of top coins to use
        
    Returns:
        List of symbol strings
    """
    if HAS_UNIVERSE_SELECTOR:
        try:
            logger.info(f"Fetching top-{n} coins by volume across exchanges...")
            coins = get_top_n_pairs(n=n, force_refresh=True)
            if coins:
                logger.info(f"Using {len(coins)} coins from universe selector")
                return coins
        except Exception as e:
            logger.warning(f"Universe selector failed: {e}, using static list")
    
    # Fallback to static list
    return TOP_50_COINS[:n]


def load_historical_data(
    symbol: str,
    timeframe: str = '1h',
    days_back: int = 180,
    exchange_id: str = 'binance'
) -> pd.DataFrame:
    """
    Load historical OHLCV data for a symbol.

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Timeframe ('15m', '1h', etc.)
        days_back: Days of historical data to load
        exchange_id: Exchange to use

    Returns:
        DataFrame with OHLCV data
    """
    try:
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

        # Calculate timestamps
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        # Convert to milliseconds
        since = int(start_time.timestamp() * 1000)
        limit = 1000  # Max candles per request

        all_ohlcv = []

        logger.info(f"Loading {symbol} data from {start_time.date()} to {end_time.date()}")

        while since < int(end_time.timestamp() * 1000):
            try:
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=limit
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # Move to next batch
                since = ohlcv[-1][0] + 1

                # Rate limiting
                exchange.sleep(exchange.rateLimit / 1000)

            except Exception as e:
                logger.warning(f"Error fetching batch for {symbol}: {e}")
                break

        if not all_ohlcv:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Convert to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        logger.info(f"  [OK] Loaded {len(df)} candles for {symbol}")

        return df

    except Exception as e:
        logger.error(f"  ✗ Failed to load {symbol}: {e}")
        return None


def train_model(n_coins: int = 20):
    """
    Main training function.
    
    Args:
        n_coins: Number of top coins to train on (default: 20 for less noise)
    """
    config = TRAINING_CONFIG
    
    print("=" * 80)
    print("LIGHTGBM TRAINING - BARRIER LABELS (TP before SL)")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Timeframe: {config['timeframe']}")
    print(f"  Days back: {config['days_back']}")
    print(f"  Barrier labels: TP={config['tp_atr_mult']}*ATR, SL={config['sl_atr_mult']}*ATR")
    print(f"  Horizon: {config['horizon_bars']} bars ({config['horizon_bars']}h)")
    print(f"  Target coins: {n_coins}")

    # Get coins to train on
    training_coins = get_training_coins(n=n_coins)

    # Data collection
    all_data = []
    successful_coins = []

    print(f"\n{'='*80}")
    print("PHASE 1: DATA COLLECTION")
    print(f"{'='*80}\n")

    for i, coin in enumerate(training_coins, 1):
        print(f"[{i}/{len(training_coins)}] {coin}...", end=" ")

        df = load_historical_data(
            symbol=coin,
            timeframe=config['timeframe'],
            days_back=config['days_back'],
            exchange_id='binance'
        )

        if df is not None and len(df) >= config['min_candles']:
            all_data.append(df)
            successful_coins.append(coin)
            print(f"[OK] {len(df):,} candles")
        else:
            print(f"[SKIP] Insufficient data")

    # Combine all data
    if not all_data:
        logger.error("No data collected! Exiting.")
        return None

    print(f"\n{'='*80}")
    print(f"DATA COLLECTION SUMMARY")
    print(f"{'='*80}")
    print(f"Successfully loaded: {len(successful_coins)}/{len(training_coins)} coins")
    print(f"Total candles: {sum(len(df) for df in all_data):,}")

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Combined dataset: {len(combined_df):,} candles")

    # Sort by timestamp
    combined_df = combined_df.sort_index()

    # Model training
    print(f"\n{'='*80}")
    print("PHASE 2: MODEL TRAINING (BARRIER LABELS)")
    print(f"{'='*80}\n")

    model = LightGBMSignalGenerator()

    try:
        metrics = model.train(
            df=combined_df,
            num_boost_round=500,
            early_stopping_rounds=50,
            test_size=0.2,
            use_new_features=config['use_new_features'],
            use_barrier_labels=config['use_barrier_labels'],
            tp_atr_mult=config['tp_atr_mult'],
            sl_atr_mult=config['sl_atr_mult'],
            horizon_bars=config['horizon_bars'],
        )

        # Display results
        print(f"\n{'='*80}")
        print("TRAINING RESULTS")
        print(f"{'='*80}")
        print(f"Accuracy: {metrics['accuracy']:.4f}")
        print(f"Total iterations: {metrics['num_iterations']}")

        if 'train_accuracy' in metrics:
            print(f"Train accuracy: {metrics['train_accuracy']:.4f}")
        if 'val_accuracy' in metrics:
            print(f"Val accuracy: {metrics['val_accuracy']:.4f}")

        print(f"\n{'='*80}")
        print("TOP 20 MOST IMPORTANT FEATURES")
        print(f"{'='*80}")

        for i, (feature, importance) in enumerate(metrics['top_features'][:20], 1):
            print(f"{i:2d}. {feature:40s} {importance:10.1f}")

        print(f"\n{'='*80}")
        print("CLASS DISTRIBUTION")
        print(f"{'='*80}")

        if 'class_distribution' in metrics:
            for class_name, count in metrics['class_distribution'].items():
                pct = (count / sum(metrics['class_distribution'].values())) * 100
                print(f"{class_name:10s}: {count:6d} ({pct:5.1f}%)")

        # Save model
        print(f"\n{'='*80}")
        print("PHASE 3: MODEL SAVING")
        print(f"{'='*80}\n")

        # Create models directory if needed
        models_dir = Path(__file__).parent.parent / "models"
        models_dir.mkdir(exist_ok=True)

        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = models_dir / f"lightgbm_enhanced_{timestamp}.pkl"

        model.save_model(str(model_path))

        print(f"[OK] Model saved: {model_path}")

        # Also save as latest
        latest_path = models_dir / "lightgbm_latest.pkl"
        model.save_model(str(latest_path))
        print(f"[OK] Model saved: {latest_path}")

        # Save training metadata
        metadata_path = models_dir / f"training_metadata_{timestamp}.txt"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(f"Training Metadata\n")
            f.write(f"=" * 80 + "\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Coins used: {len(successful_coins)}\n")
            f.write(f"Total samples: {len(combined_df):,}\n")
            f.write(f"Timeframe: {config['timeframe']}\n")
            f.write(f"Days back: {config['days_back']}\n")
            f.write(f"Enhanced features: {config['use_new_features']}\n")
            f.write(f"Barrier labels: {config['use_barrier_labels']}\n")
            f.write(f"  TP ATR mult: {config['tp_atr_mult']}\n")
            f.write(f"  SL ATR mult: {config['sl_atr_mult']}\n")
            f.write(f"  Horizon bars: {config['horizon_bars']}\n")
            f.write(f"Total features: {len(model.feature_names)}\n\n")
            f.write(f"Accuracy: {metrics['accuracy']:.4f}\n")
            f.write(f"Iterations: {metrics['num_iterations']}\n\n")
            f.write(f"Coins:\n")
            for coin in successful_coins:
                f.write(f"  - {coin}\n")
            f.write(f"\nTop 20 features:\n")
            for i, (feature, importance) in enumerate(metrics['top_features'][:20], 1):
                f.write(f"  {i:2d}. {feature:40s} {importance:10.1f}\n")

        print(f"[OK] Metadata saved: {metadata_path}")

        print(f"\n{'='*80}")
        print("TRAINING COMPLETE!")
        print(f"{'='*80}\n")

        return model, metrics

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train LightGBM model with barrier labels")
    parser.add_argument('--coins', type=int, default=20, help='Number of top coins to train on (default: 20)')
    args = parser.parse_args()
    
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    result = train_model(n_coins=args.coins)

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if result:
        print("[SUCCESS] Training succeeded!")
    else:
        print("[FAILED] Training failed!")
        sys.exit(1)
