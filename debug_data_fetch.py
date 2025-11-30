import ccxt
import time
import sys


def debug_fetch():
    print("--- Debugging Data Fetching ---")
    print(f"CCXT Version: {ccxt.__version__}")

    exchange_id = "binance"
    symbol = "BTC/USDT"

    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({"enableRateLimit": True, "options": {"defaultType": "spot"}})

        print(f"Connecting to {exchange_id}...")
        exchange.load_markets()
        print(f"Markets loaded. Total: {len(exchange.markets)}")

        if symbol in exchange.markets:
            print(f"Symbol {symbol} found.")
        else:
            print(f"Symbol {symbol} NOT found!")
            # Try to list some symbols
            print("First 5 symbols:", list(exchange.markets.keys())[:5])
            return

        print(f"Fetching OHLCV for {symbol}...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=5)

        if ohlcv:
            print(f"Success! Received {len(ohlcv)} candles.")
            print("Last candle:", ohlcv[-1])
        else:
            print("Result is empty.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_fetch()
