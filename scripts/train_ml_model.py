"""
Training script for LSTM signal generator.
Downloads historical data and trains the model.
"""

import asyncio
import sys
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ml.lstm_signal_generator import LSTMSignalGenerator
from utils.async_exchange import get_async_exchange
from utils.logger_config import setup_logging

logger = setup_logging()


async def download_training_data(
    symbols: list[str],
    timeframe: str = "15m",
    days: int = 365,
) -> dict[str, pd.DataFrame]:
    """
    Download historical OHLCV data for training.

    Args:
        symbols: List of trading pairs
        timeframe: Timeframe to download
        days: Number of days of history

    Returns:
        Dictionary of {symbol: DataFrame}
    """
    logger.info(f"Downloading {days} days of {timeframe} data for {len(symbols)} symbols...")

    exchange = await get_async_exchange("binance")

    # Calculate number of candles needed
    timeframe_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
    minutes = timeframe_minutes.get(timeframe, 15)
    candles_needed = int((days * 24 * 60) / minutes)

    # Fetch data for all symbols
    data_dict = await exchange.fetch_ohlcv_multi(
        symbols=symbols,
        timeframe=timeframe,
        limit=min(candles_needed, 1000),  # CCXT limit
    )

    # Filter out None values
    valid_data = {sym: df for sym, df in data_dict.items() if df is not None and len(df) > 200}

    logger.info(f"Downloaded data for {len(valid_data)}/{len(symbols)} symbols")

    await exchange.close()
    return valid_data


def prepare_training_labels(df: pd.DataFrame, forward_periods: int = 8, threshold: float = 0.005) -> pd.Series:
    """
    Create training labels based on future price movement.
    
    UPDATED: More sensitive thresholds for volatile crypto market:
    - threshold: 0.5% (was 1%) - captures smaller moves
    - forward_periods: 8 (was 5) - 2 hours on 15m chart for better signal capture

    Args:
        df: OHLCV DataFrame
        forward_periods: Periods to look ahead (8 periods = 2h on 15m)
        threshold: Price change threshold for signal (0.5%)

    Returns:
        Series with labels (0=sell, 1=hold, 2=buy)
    """
    future_returns = df["close"].shift(-forward_periods) / df["close"] - 1

    labels = pd.Series(1, index=df.index)  # Default: HOLD

    # BUY signal if price goes up > threshold (0.5%)
    labels[future_returns > threshold] = 2

    # SELL signal if price goes down > threshold (-0.5%)
    labels[future_returns < -threshold] = 0

    return labels


async def train_model(
    symbols: list[str] = None,
    timeframe: str = "15m",
    training_days: int = 365,
    epochs: int = 50,
    batch_size: int = 32,
    model_save_path: str = "models/lstm_model.h5",
):
    """
    Train LSTM model on historical data.

    Args:
        symbols: Trading pairs to train on (None for top volume pairs)
        timeframe: Timeframe
        training_days: Days of historical data
        epochs: Training epochs
        batch_size: Batch size
        model_save_path: Path to save trained model
    """
    logger.info("=" * 80)
    logger.info("LSTM MODEL TRAINING")
    logger.info("=" * 80)

    # Get symbols
    if symbols is None:
        logger.info("Getting top volume pairs...")
        exchange = await get_async_exchange("binance")
        tickers = await exchange.fetch_tickers()
        usdt_pairs = {k: v for k, v in tickers.items() if k.endswith("/USDT")}
        top_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1].get("quoteVolume", 0), reverse=True)
        symbols = [pair[0] for pair in top_pairs[:50]]  # Top 50
        await exchange.close()

    logger.info(f"Training on {len(symbols)} symbols: {symbols[:5]}...")

    # Download data
    data_dict = await download_training_data(symbols, timeframe, training_days)

    if len(data_dict) == 0:
        logger.error("No data downloaded! Exiting.")
        return

    # Combine all data for training
    all_data = []
    for symbol, df in data_dict.items():
        try:
            # Add labels
            df["label"] = prepare_training_labels(df)

            # Add symbol identifier
            df["symbol"] = symbol

            all_data.append(df)

        except Exception as e:
            logger.warning(f"Error processing {symbol}: {e}")

    # Combine into single DataFrame
    combined_df = pd.concat(all_data, ignore_index=False)
    logger.info(f"Combined dataset: {len(combined_df)} samples")

    # Initialize and train model
    logger.info("Initializing LSTM model...")
    model = LSTMSignalGenerator(lookback_periods=60)

    logger.info(f"Training for {epochs} epochs...")
    history = model.train(ohlcv_df=combined_df, epochs=epochs, batch_size=batch_size, validation_split=0.2)

    # Save model
    Path(model_save_path).parent.mkdir(parents=True, exist_ok=True)
    model.save_model(model_save_path)

    logger.info("=" * 80)
    logger.info("TRAINING COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Final accuracy: {history['final_accuracy']:.4f}")
    logger.info(f"Validation accuracy: {history['val_accuracy']:.4f}")
    logger.info(f"Model saved to: {model_save_path}")

    return model, history


if __name__ == "__main__":
    """Run training."""
    import argparse

    parser = argparse.ArgumentParser(description="Train LSTM trading model")
    parser.add_argument("--symbols", nargs="+", help="Trading pairs to train on")
    parser.add_argument("--timeframe", default="15m", help="Timeframe (default: 15m)")
    parser.add_argument("--days", type=int, default=365, help="Training days (default: 365)")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs (default: 50)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--output", default="models/lstm_model.h5", help="Model save path")

    args = parser.parse_args()

    # Run training
    asyncio.run(
        train_model(
            symbols=args.symbols,
            timeframe=args.timeframe,
            training_days=args.days,
            epochs=args.epochs,
            batch_size=args.batch_size,
            model_save_path=args.output,
        )
    )
