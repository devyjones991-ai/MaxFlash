import ccxt
import time
import sys


def debug_exchanges():
    print("--- Debugging Exchanges ---")
    exchanges = ["bybit", "okx", "kraken"]

    for exchange_id in exchanges:
        print(f"\nTesting {exchange_id}...")
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({"enableRateLimit": True, "options": {"defaultType": "spot"}})

            print(f"Connecting to {exchange_id}...")
            start = time.time()
            markets = exchange.load_markets()
            duration = time.time() - start

            print(f"Success! Loaded {len(markets)} markets in {duration:.2f}s")

            symbol = "BTC/USDT"
            if symbol in markets:
                print(f"Symbol {symbol} found.")
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=5)
                print(f"Fetched {len(ohlcv)} candles.")
            else:
                print(f"Symbol {symbol} NOT found. Available: {list(markets.keys())[:5]}")

        except Exception as e:
            print(f"FAILED {exchange_id}: {e}")
            # import traceback
            # traceback.print_exc()


if __name__ == "__main__":
    debug_exchanges()
