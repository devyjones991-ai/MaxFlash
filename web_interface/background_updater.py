"""
Background Market Data Updater for MaxFlash Dashboard v4.0.

Использует MultiSourceDataProvider для получения данных из нескольких источников:
- CoinGecko (prices, market data)
- KuCoin/Kraken/OKX (OHLCV для графиков)
- ExchangeRate-API/CBR (Forex курсы)

Полностью независим от Binance API.
"""
import os
import sys
import time
import json
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path
import atexit
from typing import Dict, Any, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger_config import setup_logging

# Setup logging
logger = setup_logging()
logger.setLevel(logging.INFO)

# ============ DUPLICATE PROCESS PROTECTION ============
PID_FILE = "/tmp/maxflash_bg_updater.pid"
RUNNING = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global RUNNING
    logger.info(f"Received signal {signum}, shutting down...")
    RUNNING = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def check_and_create_pidfile():
    """Prevent duplicate processes using PID lock file."""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                old_pid = f.read().strip()
                if old_pid:
                    try:
                        os.kill(int(old_pid), 0)
                        logger.error(f"Another background_updater is already running (PID {old_pid}). Exiting.")
                        sys.exit(1)
                    except (ProcessLookupError, ValueError):
                        pass

        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

        logger.info(f"PID file created: {PID_FILE} (PID: {os.getpid()})")

    except Exception as e:
        logger.error(f"Error with PID file: {e}")


def cleanup_pidfile():
    """Remove PID file on exit."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info("PID file removed")
    except Exception:
        pass


atexit.register(cleanup_pidfile)


# ============ CONFIG ============
UPDATE_INTERVAL_SECONDS = 90  # Увеличен для снижения нагрузки на API
CACHE_FILE_PATH = str(PROJECT_ROOT / "data" / "market_cache.json")
OHLCV_CACHE_PATH = str(PROJECT_ROOT / "data" / "ohlcv_cache.json")
FOREX_CACHE_PATH = str(PROJECT_ROOT / "data" / "forex_cache.json")

# Ensure data directory exists
os.makedirs(PROJECT_ROOT / "data", exist_ok=True)

# Top coins to monitor
TOP_COINS = [
    "BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "DOGE", "AVAX", "DOT", "MATIC",
    "LINK", "ATOM", "LTC", "UNI", "XLM", "NEAR", "APT", "ARB", "OP", "SUI",
    "INJ", "FET", "RENDER", "TIA", "SEI", "PEPE", "WIF", "BONK", "FLOKI", "SHIB",
    "TRX", "ETC", "FIL", "HBAR", "VET", "STX", "IMX", "GRT", "ALGO", "FTM",
]

# Forex pairs to monitor
FOREX_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD",
    "USD/RUB", "EUR/RUB", "EUR/GBP"
]


def get_signal_from_change(change_24h: float) -> tuple:
    """Generate signal based on 24h price change."""
    reasons = []

    if change_24h <= -8:
        signal = "BUY"
        score = 85
        reasons.append(f"📉 Сильное падение {change_24h:.1f}%")
    elif change_24h <= -4:
        signal = "BUY"
        score = 70
        reasons.append(f"📉 Падение {change_24h:.1f}%")
    elif change_24h >= 8:
        signal = "SELL"
        score = 85
        reasons.append(f"📈 Сильный рост {change_24h:+.1f}%")
    elif change_24h >= 4:
        signal = "SELL"
        score = 70
        reasons.append(f"📈 Рост {change_24h:+.1f}%")
    else:
        signal = "HOLD"
        score = 50
        if change_24h > 0:
            reasons.append(f"📊 Небольшой рост {change_24h:+.1f}%")
        else:
            reasons.append(f"📊 Боковик {change_24h:.1f}%")

    return signal, score, reasons


# Blacklist stablecoins and wrapped/pegged tokens that aren't real trading coins
COIN_BLACKLIST = {
    'usdt', 'usdc', 'busd', 'dai', 'tusd', 'usdp', 'usdd', 'gusd', 'frax', 'lusd',
    'usdt0', 'usd1', 'usdc.e', 'usdt.e', 'wbtc', 'weth', 'steth', 'wsteth', 'reth',
    'cbeth', 'hbtc', 'renbtc', 'tbtc', 'sbtc', 'paxg', 'xaut', 'fdusd', 'pyusd',
    'eurc', 'eurs', 'eurt', 'first digital usd', 'true usd', 'pax dollar',
}


def fetch_crypto_data() -> List[Dict[str, Any]]:
    """Fetch crypto data using MultiSourceDataProvider."""
    try:
        from utils.multi_source_provider import get_data_provider

        provider = get_data_provider()
        data = []

        # Get market overview from CoinGecko
        overview = provider.get_market_overview()
        crypto_markets = overview.get("crypto_markets", [])

        if crypto_markets:
            for coin in crypto_markets:
                if len(data) >= 50:  # Stop at 50 real coins
                    break
                try:
                    symbol = coin.get("symbol", "").upper()
                    name = coin.get("name", "").lower()

                    # Skip stablecoins and wrapped tokens
                    if symbol.lower() in COIN_BLACKLIST or name in COIN_BLACKLIST:
                        continue

                    price = coin.get("current_price", 0)
                    change = coin.get("price_change_percentage_24h", 0) or 0
                    volume = coin.get("total_volume", 0) or 0
                    high = coin.get("high_24h", price) or price
                    low = coin.get("low_24h", price) or price
                    market_cap = coin.get("market_cap", 0) or 0

                    signal, score, reasons = get_signal_from_change(change)

                    data.append({
                        'symbol': symbol,
                        'full_symbol': f"{symbol}/USDT",
                        'name': coin.get("name", symbol),
                        'price': price,
                        'change_24h': change,
                        'change_1h': coin.get("price_change_percentage_1h_in_currency", 0) or 0,
                        'change_7d': coin.get("price_change_percentage_7d_in_currency", 0) or 0,
                        'volume': volume,
                        'market_cap': market_cap,
                        'high': high,
                        'low': low,
                        'signal': signal,
                        'signal_score': score,
                        'reasons': reasons,
                        'rank': coin.get("market_cap_rank", 999),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Error processing coin {coin.get('symbol', '?')}: {e}")

        # Sort by market cap (highest first)
        data.sort(key=lambda x: x.get('market_cap', 0), reverse=True)

        logger.info(f"Fetched {len(data)} coins from CoinGecko")
        return data

    except ImportError:
        logger.warning("MultiSourceProvider not available, using fallback")
        return fetch_crypto_data_fallback()
    except Exception as e:
        logger.error(f"Error fetching crypto data: {e}")
        return fetch_crypto_data_fallback()


def fetch_crypto_data_fallback() -> List[Dict[str, Any]]:
    """Fallback: fetch directly from CoinGecko API."""
    import requests

    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,  # Fetch more to filter out stablecoins
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d"
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        coins = response.json()

        data = []
        for coin in coins:
            if len(data) >= 50:
                break
            symbol = coin.get("symbol", "").upper()
            name = coin.get("name", "").lower()

            # Skip stablecoins and wrapped tokens
            if symbol.lower() in COIN_BLACKLIST or name in COIN_BLACKLIST:
                continue

            price = coin.get("current_price", 0)
            change = coin.get("price_change_percentage_24h", 0) or 0

            signal, score, reasons = get_signal_from_change(change)

            data.append({
                'symbol': symbol,
                'full_symbol': f"{symbol}/USDT",
                'name': coin.get("name", symbol),
                'price': price,
                'change_24h': change,
                'volume': coin.get("total_volume", 0) or 0,
                'market_cap': coin.get("market_cap", 0) or 0,
                'high': coin.get("high_24h", price) or price,
                'low': coin.get("low_24h", price) or price,
                'signal': signal,
                'signal_score': score,
                'reasons': reasons,
                'rank': coin.get("market_cap_rank", 999),
                'updated_at': datetime.now(timezone.utc).isoformat()
            })

        logger.info(f"Fetched {len(data)} coins (fallback)")
        return data

    except Exception as e:
        logger.error(f"Fallback fetch error: {e}")
        return []


def fetch_forex_data() -> List[Dict[str, Any]]:
    """Fetch forex rates."""
    try:
        from utils.multi_source_provider import get_data_provider

        provider = get_data_provider()
        forex_rates = provider.forex_provider.get_all_rates()

        data = []
        for pair in FOREX_PAIRS:
            rate = forex_rates.get(pair) or forex_rates.get(pair.replace("/", "_"))
            if rate:
                data.append({
                    'pair': pair,
                    'rate': rate,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })

        logger.info(f"Fetched {len(data)} forex pairs")
        return data

    except ImportError:
        return fetch_forex_fallback()
    except Exception as e:
        logger.error(f"Error fetching forex: {e}")
        return fetch_forex_fallback()


def fetch_forex_fallback() -> List[Dict[str, Any]]:
    """Fallback forex fetch via ExchangeRate-API."""
    import requests

    try:
        response = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=10
        )
        response.raise_for_status()
        rates = response.json().get("rates", {})

        data = []
        for pair in FOREX_PAIRS:
            base, quote = pair.split("/")
            if base == "USD":
                rate = rates.get(quote)
            elif quote == "USD":
                base_rate = rates.get(base)
                rate = 1 / base_rate if base_rate else None
            else:
                base_rate = rates.get(base)
                quote_rate = rates.get(quote)
                rate = quote_rate / base_rate if base_rate and quote_rate else None

            if rate:
                data.append({
                    'pair': pair,
                    'rate': rate,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })

        return data

    except Exception as e:
        logger.error(f"Forex fallback error: {e}")
        return []


def fetch_ohlcv_for_charts() -> Dict[str, Any]:
    """Fetch OHLCV data for charts (top 10 coins only to save API calls)."""
    try:
        from utils.multi_source_provider import get_data_provider

        provider = get_data_provider()
        ohlcv_data = {}

        # Only fetch for top 10 coins to avoid rate limits
        top_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"]

        for symbol in top_symbols:
            try:
                df = provider.get_ohlcv(symbol, timeframe="1h", limit=100)
                if df is not None and not df.empty:
                    # Convert to JSON-serializable format
                    ohlcv_data[symbol] = {
                        "timestamps": df.index.strftime("%Y-%m-%d %H:%M").tolist(),
                        "open": df["open"].tolist(),
                        "high": df["high"].tolist(),
                        "low": df["low"].tolist(),
                        "close": df["close"].tolist(),
                        "volume": df["volume"].tolist() if "volume" in df.columns else [],
                    }
                    logger.info(f"OHLCV loaded for {symbol}: {len(df)} candles")
            except Exception as e:
                logger.warning(f"OHLCV error for {symbol}: {e}")

        return ohlcv_data

    except ImportError:
        logger.warning("MultiSourceProvider not available for OHLCV")
        return {}
    except Exception as e:
        logger.error(f"OHLCV fetch error: {e}")
        return {}


def save_json_atomic(data: Any, filepath: str):
    """Save JSON atomically to prevent corruption."""
    temp_file = filepath + ".tmp"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        os.replace(temp_file, filepath)
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)


def run_update_cycle():
    """Run a single update cycle."""
    try:
        start_time = time.time()
        logger.info("=" * 50)
        logger.info("Starting market data update cycle...")

        # 1. Fetch crypto data
        crypto_data = fetch_crypto_data()
        if crypto_data:
            save_json_atomic({
                'timestamp': time.time(),
                'source': 'multi_source_provider',
                'count': len(crypto_data),
                'data': crypto_data
            }, CACHE_FILE_PATH)
            logger.info(f"Saved {len(crypto_data)} coins to cache")

        # 2. Fetch forex data
        forex_data = fetch_forex_data()
        if forex_data:
            save_json_atomic({
                'timestamp': time.time(),
                'source': 'forex_provider',
                'data': forex_data
            }, FOREX_CACHE_PATH)
            logger.info(f"Saved {len(forex_data)} forex pairs to cache")

        # 3. Fetch OHLCV for charts (every 5 minutes to reduce load)
        cycle_num = getattr(run_update_cycle, 'cycle_num', 0) + 1
        run_update_cycle.cycle_num = cycle_num

        if cycle_num % 5 == 1:  # Every 5th cycle (~7.5 min)
            ohlcv_data = fetch_ohlcv_for_charts()
            if ohlcv_data:
                save_json_atomic({
                    'timestamp': time.time(),
                    'data': ohlcv_data
                }, OHLCV_CACHE_PATH)
                logger.info(f"Saved OHLCV data for {len(ohlcv_data)} pairs")

        elapsed = time.time() - start_time
        logger.info(f"Update cycle completed in {elapsed:.2f}s")

    except Exception as e:
        logger.error(f"Critical error in update cycle: {e}", exc_info=True)


def main():
    check_and_create_pidfile()

    logger.info("=" * 60)
    logger.info("Starting Background Market Data Updater v4.0")
    logger.info("Sources: CoinGecko, KuCoin, Kraken, OKX, ExchangeRate-API")
    logger.info(f"Update interval: {UPDATE_INTERVAL_SECONDS}s")
    logger.info(f"Cache path: {CACHE_FILE_PATH}")
    logger.info("=" * 60)

    # Initial update
    run_update_cycle()

    while RUNNING:
        time.sleep(UPDATE_INTERVAL_SECONDS)
        if RUNNING:
            run_update_cycle()

    logger.info("Background updater stopped")


if __name__ == "__main__":
    main()
