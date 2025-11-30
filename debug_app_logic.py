import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.insert(0, "/home/devyjones/MaxFlash")

from utils.exchange_manager import ExchangeManager
from utils.market_data_manager import MarketDataManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_app_logic():
    print("--- Debugging App Logic ---")

    try:
        # Test ExchangeManager directly
        print("\n1. Testing ExchangeManager...")
        em = ExchangeManager()
        print(f"Exchanges: {list(em.exchanges.keys())}")

        symbol = "BTC/USDT"
        print(f"Fetching OHLCV for {symbol} via ExchangeManager...")
        ohlcv = em.fetch_ohlcv(symbol, timeframe="15m", limit=5)

        if ohlcv:
            print(f"ExchangeManager Success! {len(ohlcv)} candles.")
        else:
            print("ExchangeManager Failed: Returned None or empty.")

        # Test MarketDataManager
        print("\n2. Testing MarketDataManager...")
        mdm = MarketDataManager()
        print(f"Fetching OHLCV for {symbol} via MarketDataManager...")
        df = mdm.get_ohlcv(symbol, timeframe="15m", limit=5)

        if df is not None and not df.empty:
            print(f"MarketDataManager Success! DataFrame shape: {df.shape}")
            print(df.tail())
        else:
            print("MarketDataManager Failed: Returned None or empty.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_app_logic()
