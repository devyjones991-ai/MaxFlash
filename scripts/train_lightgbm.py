"""
Comprehensive LightGBM training script for MaxFlash.
Trains model on 6 months of historical data from top 50 coins with enhanced features.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import ccxt
from datetime import datetime, timedelta
from ml.lightgbm_model import LightGBMSignalGenerator
from utils.logger_config import setup_logging

logger = setup_logging()

# Top 50 coins by market cap (excluding stablecoins)
TOP_50_COINS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT",
    "TRX/USDT", "LINK/USDT", "ATOM/USDT", "UNI/USDT", "LTC/USDT",
    "XLM/USDT", "NEAR/USDT", "ALGO/USDT", "BCH/USDT", "FIL/USDT",
    "ARB/USDT", "OP/USDT", "APT/USDT", "SUI/USDT", "INJ/USDT",
    "SEI/USDT", "RUNE/USDT", "FET/USDT", "GRT/USDT", "SAND/USDT",
    "MANA/USDT", "AXS/USDT", "THETA/USDT", "XTZ/USDT", "EOS/USDT",
    "AAVE/USDT", "MKR/USDT", "SNX/USDT", "CRV/USDT", "LDO/USDT",
    "IMX/USDT", "RNDR/USDT", "FTM/USDT", "APE/USDT", "CHZ/USDT",
    "EGLD/USDT", "FLOW/USDT", "ICP/USDT", "HBAR/USDT", "QNT/USDT"
]


def load_historical_data(
    symbol: str,
    timeframe: str = '15m',
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

        logger.info(f"  ✓ Loaded {len(df)} candles for {symbol}")

        return df

    except Exception as e:
        logger.error(f"  ✗ Failed to load {symbol}: {e}")
        return None


def train_model():
    """
    Main training function.
    """
    print("=" * 80)
    print("LIGHTGBM TRAINING - 6 MONTHS - 50 COINS - ENHANCED FEATURES")
    print("=" * 80)

    # Configuration
    TIMEFRAME = '15m'
    DAYS_BACK = 180  # 6 months
    EXCHANGE = 'binance'
    MIN_CANDLES = 1000  # Minimum candles required

    # Data collection
    all_data = []
    successful_coins = []

    print(f"\n{'='*80}")
    print("PHASE 1: DATA COLLECTION")
    print(f"{'='*80}\n")

    for i, coin in enumerate(TOP_50_COINS, 1):
        print(f"[{i}/{len(TOP_50_COINS)}] {coin}...", end=" ")

        df = load_historical_data(
            symbol=coin,
            timeframe=TIMEFRAME,
            days_back=DAYS_BACK,
            exchange_id=EXCHANGE
        )

        if df is not None and len(df) >= MIN_CANDLES:
            all_data.append(df)
            successful_coins.append(coin)
            print(f"✓ {len(df):,} candles")
        else:
            print(f"✗ Insufficient data")

    # Combine all data
    if not all_data:
        logger.error("No data collected! Exiting.")
        return None

    print(f"\n{'='*80}")
    print(f"DATA COLLECTION SUMMARY")
    print(f"{'='*80}")
    print(f"Successfully loaded: {len(successful_coins)}/{len(TOP_50_COINS)} coins")
    print(f"Total candles: {sum(len(df) for df in all_data):,}")

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Combined dataset: {len(combined_df):,} candles")

    # Sort by timestamp
    combined_df = combined_df.sort_index()

    # Model training
    print(f"\n{'='*80}")
    print("PHASE 2: MODEL TRAINING")
    print(f"{'='*80}\n")

    model = LightGBMSignalGenerator()

    try:
        metrics = model.train(
            df=combined_df,
            num_boost_round=1000,
            early_stopping_rounds=50,
            test_size=0.2,
            use_new_features=True  # ← Enable enhanced features!
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

        print(f"✓ Model saved: {model_path}")

        # Also save as latest
        latest_path = models_dir / "lightgbm_latest.pkl"
        model.save_model(str(latest_path))
        print(f"✓ Model saved: {latest_path}")

        # Save training metadata
        metadata_path = models_dir / f"training_metadata_{timestamp}.txt"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(f"Training Metadata\n")
            f.write(f"=" * 80 + "\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Coins used: {len(successful_coins)}\n")
            f.write(f"Total samples: {len(combined_df):,}\n")
            f.write(f"Timeframe: {TIMEFRAME}\n")
            f.write(f"Days back: {DAYS_BACK}\n")
            f.write(f"Enhanced features: Yes (ADX, OBV, VWAP, Donchian)\n")
            f.write(f"Total features: {len(model.feature_names)}\n\n")
            f.write(f"Accuracy: {metrics['accuracy']:.4f}\n")
            f.write(f"Iterations: {metrics['num_iterations']}\n\n")
            f.write(f"Coins:\n")
            for coin in successful_coins:
                f.write(f"  - {coin}\n")
            f.write(f"\nTop 20 features:\n")
            for i, (feature, importance) in enumerate(metrics['top_features'][:20], 1):
                f.write(f"  {i:2d}. {feature:40s} {importance:10.1f}\n")

        print(f"✓ Metadata saved: {metadata_path}")

        print(f"\n{'='*80}")
        print("TRAINING COMPLETE! 🎉")
        print(f"{'='*80}\n")

        return model, metrics

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    result = train_model()

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if result:
        print("✓ Training succeeded!")
    else:
        print("✗ Training failed!")
        sys.exit(1)
