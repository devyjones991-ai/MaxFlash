import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.insert(0, "/home/devyjones/MaxFlash")

from utils.exchange_manager import ExchangeManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_bybit():
    print("--- Debugging Bybit Logic ---")

    try:
        em = ExchangeManager()
        symbol = "BTC/USDT"

        # Force Bybit
        print(f"\nFetching OHLCV for {symbol} via Bybit...")
        ohlcv = em.fetch_ohlcv(symbol, timeframe="15m", limit=5, exchange_id="bybit")

        if ohlcv:
            print(f"Bybit Success! {len(ohlcv)} candles.")
        else:
            print("Bybit Failed.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_bybit()
