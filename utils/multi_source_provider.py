"""
Multi-Source Data Provider - независимый от Binance провайдер данных.

Использует несколько источников с автоматическим fallback:
1. CoinGecko (бесплатный, надёжный, без бана IP)
2. KuCoin (без ограничений для публичных данных)
3. Kraken (стабильный, европейский)
4. OKX (резервный)

Для Forex:
1. ExchangeRate-API (бесплатный)
2. Twelve Data (бесплатный tier)
3. CBR (для RUB пар)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import threading

import requests
import pandas as pd

try:
    import ccxt
    import ccxt.async_support as ccxt_async
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    ccxt = None
    ccxt_async = None

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Доступные источники данных."""
    COINGECKO = "coingecko"
    KUCOIN = "kucoin"
    KRAKEN = "kraken"
    OKX = "okx"
    BYBIT = "bybit"
    # Forex sources
    EXCHANGERATE_API = "exchangerate-api"
    TWELVE_DATA = "twelve-data"
    CBR = "cbr"


@dataclass
class SourceHealth:
    """Статус здоровья источника данных."""
    source: DataSource
    is_healthy: bool
    last_success: Optional[datetime]
    last_error: Optional[str]
    error_count: int
    avg_latency_ms: float


class RateLimiter:
    """Rate limiter для предотвращения банов."""

    def __init__(self, calls_per_minute: int = 30):
        self.calls_per_minute = calls_per_minute
        self.calls: List[float] = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Ждём если превышен лимит."""
        with self.lock:
            now = time.time()
            # Удаляем старые вызовы (>1 минуты)
            self.calls = [t for t in self.calls if now - t < 60]

            if len(self.calls) >= self.calls_per_minute:
                # Ждём пока освободится слот
                sleep_time = 60 - (now - self.calls[0]) + 0.1
                if sleep_time > 0:
                    logger.debug(f"Rate limit: sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)

            self.calls.append(time.time())


class CoinGeckoProvider:
    """
    CoinGecko API Provider - бесплатный и надёжный.

    Лимиты:
    - 10-30 calls/minute (бесплатный)
    - Нет бана IP при соблюдении лимитов
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    # Маппинг символов на CoinGecko ID
    SYMBOL_TO_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "XRP": "ripple",
        "SOL": "solana",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "AVAX": "avalanche-2",
        "DOT": "polkadot",
        "MATIC": "matic-network",
        "LINK": "chainlink",
        "ATOM": "cosmos",
        "LTC": "litecoin",
        "UNI": "uniswap",
        "XLM": "stellar",
        "NEAR": "near",
        "APT": "aptos",
        "ARB": "arbitrum",
        "OP": "optimism",
        "SUI": "sui",
        "INJ": "injective-protocol",
        "FET": "fetch-ai",
        "RENDER": "render-token",
        "TIA": "celestia",
        "SEI": "sei-network",
        "PEPE": "pepe",
        "WIF": "dogwifcoin",
        "BONK": "bonk",
        "FLOKI": "floki",
        "SHIB": "shiba-inu",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(calls_per_minute=25)  # Консервативный лимит
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "MaxFlash/4.0"
        })
        if api_key:
            self.session.headers["x-cg-demo-api-key"] = api_key

    def _get_coin_id(self, symbol: str) -> Optional[str]:
        """Получить CoinGecko ID по символу."""
        # Убираем /USDT если есть
        clean_symbol = symbol.replace("/USDT", "").replace("/USD", "").upper()
        return self.SYMBOL_TO_ID.get(clean_symbol)

    def get_price(self, symbols: List[str]) -> Dict[str, float]:
        """Получить текущие цены для списка символов."""
        self.rate_limiter.wait_if_needed()

        # Конвертируем символы в CoinGecko IDs
        coin_ids = []
        symbol_map = {}
        for s in symbols:
            coin_id = self._get_coin_id(s)
            if coin_id:
                coin_ids.append(coin_id)
                symbol_map[coin_id] = s

        if not coin_ids:
            return {}

        try:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": ",".join(coin_ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            result = {}
            for coin_id, prices in data.items():
                symbol = symbol_map.get(coin_id)
                if symbol:
                    result[symbol] = {
                        "price": prices.get("usd", 0),
                        "change_24h": prices.get("usd_24h_change", 0),
                        "volume_24h": prices.get("usd_24h_vol", 0)
                    }

            return result

        except Exception as e:
            logger.error(f"CoinGecko price error: {e}")
            return {}

    def get_ohlcv(self, symbol: str, days: int = 7) -> Optional[pd.DataFrame]:
        """
        Получить OHLCV данные.

        CoinGecko даёт только daily/hourly данные, не идеально для 15m,
        но можно использовать как fallback.
        """
        self.rate_limiter.wait_if_needed()

        coin_id = self._get_coin_id(symbol)
        if not coin_id:
            logger.warning(f"Unknown symbol for CoinGecko: {symbol}")
            return None

        try:
            url = f"{self.BASE_URL}/coins/{coin_id}/ohlc"
            params = {"vs_currency": "usd", "days": str(days)}

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df["volume"] = 0  # CoinGecko OHLC не даёт volume

            return df

        except Exception as e:
            logger.error(f"CoinGecko OHLCV error for {symbol}: {e}")
            return None

    def get_market_data(self, limit: int = 100) -> List[Dict]:
        """Получить данные топ монет по капитализации."""
        self.rate_limiter.wait_if_needed()

        try:
            url = f"{self.BASE_URL}/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d"
            }

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"CoinGecko market data error: {e}")
            return []


class CCXTProvider:
    """
    CCXT-based provider для KuCoin, Kraken, OKX.

    Эти биржи более лояльны к публичным запросам чем Binance.
    """

    # Приоритет бирж (от лучшего к худшему)
    EXCHANGE_PRIORITY = ["kucoin", "kraken", "okx", "bybit"]

    # Маппинг символов между биржами
    SYMBOL_MAPPINGS = {
        "kucoin": {},  # KuCoin использует стандартные символы
        "kraken": {
            "BTC/USDT": "BTC/USD",
            "ETH/USDT": "ETH/USD",
        },
        "okx": {},
        "bybit": {},
    }

    def __init__(self):
        self.exchanges: Dict[str, Any] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.health: Dict[str, SourceHealth] = {}

        # Инициализируем биржи
        self._init_exchanges()

    def _init_exchanges(self):
        """Инициализация бирж."""
        if not HAS_CCXT:
            logger.warning("CCXT not installed")
            return

        exchange_configs = {
            "kucoin": {
                "enableRateLimit": True,
                "rateLimit": 200,  # 5 requests per second
                "options": {"defaultType": "spot"}
            },
            "kraken": {
                "enableRateLimit": True,
                "rateLimit": 1000,  # 1 request per second (conservative)
                "options": {"defaultType": "spot"}
            },
            "okx": {
                "enableRateLimit": True,
                "rateLimit": 100,
                "options": {"defaultType": "spot"}
            },
            "bybit": {
                "enableRateLimit": True,
                "rateLimit": 100,
                "options": {"defaultType": "spot"}
            }
        }

        for ex_id, config in exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, ex_id)
                self.exchanges[ex_id] = exchange_class(config)
                self.rate_limiters[ex_id] = RateLimiter(calls_per_minute=50)
                self.health[ex_id] = SourceHealth(
                    source=DataSource(ex_id) if ex_id in [e.value for e in DataSource] else DataSource.KUCOIN,
                    is_healthy=True,
                    last_success=None,
                    last_error=None,
                    error_count=0,
                    avg_latency_ms=0
                )
                logger.info(f"Initialized {ex_id} exchange")
            except Exception as e:
                logger.error(f"Failed to init {ex_id}: {e}")

    def _map_symbol(self, symbol: str, exchange_id: str) -> str:
        """Маппинг символа для конкретной биржи."""
        mappings = self.SYMBOL_MAPPINGS.get(exchange_id, {})
        return mappings.get(symbol, symbol)

    def _update_health(self, exchange_id: str, success: bool, error: Optional[str] = None, latency_ms: float = 0):
        """Обновить статус здоровья источника."""
        if exchange_id not in self.health:
            return

        h = self.health[exchange_id]
        if success:
            h.is_healthy = True
            h.last_success = datetime.now()
            h.error_count = 0
            # Скользящее среднее latency
            h.avg_latency_ms = (h.avg_latency_ms * 0.8 + latency_ms * 0.2) if h.avg_latency_ms > 0 else latency_ms
        else:
            h.error_count += 1
            h.last_error = error
            # Помечаем как unhealthy после 3 ошибок подряд
            if h.error_count >= 3:
                h.is_healthy = False

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
        preferred_exchange: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Получить OHLCV с автоматическим fallback между биржами.
        """
        if not HAS_CCXT:
            return None

        # Формируем приоритетный список бирж
        exchanges_to_try = []
        if preferred_exchange and preferred_exchange in self.exchanges:
            exchanges_to_try.append(preferred_exchange)

        # Добавляем здоровые биржи по приоритету
        for ex_id in self.EXCHANGE_PRIORITY:
            if ex_id not in exchanges_to_try and ex_id in self.exchanges:
                if self.health.get(ex_id, SourceHealth(DataSource.KUCOIN, True, None, None, 0, 0)).is_healthy:
                    exchanges_to_try.append(ex_id)

        # Добавляем нездоровые биржи в конец (на всякий случай)
        for ex_id in self.EXCHANGE_PRIORITY:
            if ex_id not in exchanges_to_try and ex_id in self.exchanges:
                exchanges_to_try.append(ex_id)

        for ex_id in exchanges_to_try:
            exchange = self.exchanges[ex_id]
            mapped_symbol = self._map_symbol(symbol, ex_id)

            try:
                self.rate_limiters[ex_id].wait_if_needed()

                # Загружаем markets если не загружены
                if not exchange.markets:
                    exchange.load_markets()

                # Проверяем есть ли символ
                if mapped_symbol not in exchange.markets:
                    logger.debug(f"{mapped_symbol} not found on {ex_id}")
                    continue

                start_time = time.time()
                ohlcv = exchange.fetch_ohlcv(mapped_symbol, timeframe, limit=limit)
                latency = (time.time() - start_time) * 1000

                if ohlcv and len(ohlcv) > 0:
                    df = pd.DataFrame(
                        ohlcv,
                        columns=["timestamp", "open", "high", "low", "close", "volume"]
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df.set_index("timestamp", inplace=True)

                    self._update_health(ex_id, True, latency_ms=latency)
                    logger.info(f"Got {len(df)} candles for {symbol} from {ex_id} in {latency:.0f}ms")
                    return df

            except Exception as e:
                error_msg = str(e)
                self._update_health(ex_id, False, error=error_msg)
                logger.warning(f"OHLCV error from {ex_id}: {error_msg}")
                continue

        logger.error(f"Failed to get OHLCV for {symbol} from any exchange")
        return None

    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Получить тикер с fallback."""
        if not HAS_CCXT:
            return None

        for ex_id in self.EXCHANGE_PRIORITY:
            if ex_id not in self.exchanges:
                continue

            exchange = self.exchanges[ex_id]
            mapped_symbol = self._map_symbol(symbol, ex_id)

            try:
                self.rate_limiters[ex_id].wait_if_needed()

                if not exchange.markets:
                    exchange.load_markets()

                if mapped_symbol not in exchange.markets:
                    continue

                ticker = exchange.fetch_ticker(mapped_symbol)
                self._update_health(ex_id, True)
                return ticker

            except Exception as e:
                self._update_health(ex_id, False, error=str(e))
                continue

        return None

    def fetch_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """Получить тикеры для нескольких символов."""
        result = {}

        for symbol in symbols:
            ticker = self.fetch_ticker(symbol)
            if ticker:
                result[symbol] = ticker

        return result

    def get_health_status(self) -> Dict[str, SourceHealth]:
        """Получить статус здоровья всех источников."""
        return self.health.copy()


class ForexProvider:
    """
    Провайдер данных для Forex.

    Источники:
    1. ExchangeRate-API (бесплатный, 1500 req/month)
    2. Twelve Data (бесплатный tier, 800 req/day)
    3. CBR (для RUB пар)
    """

    # Бесплатные API endpoints
    EXCHANGERATE_API_URL = "https://api.exchangerate-api.com/v4/latest"
    TWELVE_DATA_URL = "https://api.twelvedata.com"
    CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"

    # Основные Forex пары
    MAJOR_PAIRS = [
        "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
        "AUD/USD", "USD/CAD", "NZD/USD"
    ]

    CROSS_PAIRS = [
        "EUR/GBP", "EUR/JPY", "GBP/JPY", "EUR/CHF"
    ]

    RUB_PAIRS = ["USD/RUB", "EUR/RUB"]

    def __init__(self, twelve_data_api_key: Optional[str] = None):
        self.twelve_data_key = twelve_data_api_key
        self.rate_limiter = RateLimiter(calls_per_minute=20)
        self.cache: Dict[str, Tuple[datetime, Any]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.session = requests.Session()

    def _is_cache_valid(self, key: str) -> bool:
        """Проверить валидность кэша."""
        if key not in self.cache:
            return False
        cache_time, _ = self.cache[key]
        return datetime.now() - cache_time < self.cache_ttl

    def get_rates_exchangerate_api(self, base: str = "USD") -> Dict[str, float]:
        """Получить курсы через ExchangeRate-API."""
        cache_key = f"exchangerate_{base}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][1]

        try:
            self.rate_limiter.wait_if_needed()
            response = self.session.get(
                f"{self.EXCHANGERATE_API_URL}/{base}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            rates = data.get("rates", {})
            self.cache[cache_key] = (datetime.now(), rates)
            return rates

        except Exception as e:
            logger.error(f"ExchangeRate-API error: {e}")
            return {}

    def get_rates_cbr(self) -> Dict[str, float]:
        """Получить курсы ЦБ РФ."""
        cache_key = "cbr_rates"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][1]

        try:
            self.rate_limiter.wait_if_needed()
            response = self.session.get(self.CBR_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            rates = {}
            valutes = data.get("Valute", {})

            if "USD" in valutes:
                rates["USD/RUB"] = valutes["USD"]["Value"]
            if "EUR" in valutes:
                rates["EUR/RUB"] = valutes["EUR"]["Value"]

            self.cache[cache_key] = (datetime.now(), rates)
            return rates

        except Exception as e:
            logger.error(f"CBR API error: {e}")
            return {}

    def get_pair_rate(self, pair: str) -> Optional[float]:
        """Получить курс для конкретной пары."""
        base, quote = pair.replace("_", "/").split("/")

        # Для RUB пар используем ЦБ
        if quote == "RUB":
            cbr_rates = self.get_rates_cbr()
            return cbr_rates.get(pair.replace("_", "/"))

        # Для остальных - ExchangeRate-API
        if base == "USD":
            rates = self.get_rates_exchangerate_api("USD")
            return rates.get(quote)
        elif quote == "USD":
            rates = self.get_rates_exchangerate_api(base)
            usd_rate = rates.get("USD")
            return 1 / usd_rate if usd_rate else None
        else:
            # Кросс-пара: считаем через USD
            base_rates = self.get_rates_exchangerate_api(base)
            quote_usd = base_rates.get(quote)
            return quote_usd

    def get_all_rates(self) -> Dict[str, float]:
        """Получить все доступные курсы."""
        result = {}

        # USD пары
        usd_rates = self.get_rates_exchangerate_api("USD")
        for quote, rate in usd_rates.items():
            pair = f"USD/{quote}"
            result[pair] = rate

        # Инверсии для основных пар
        for pair in self.MAJOR_PAIRS:
            base, quote = pair.split("/")
            if quote == "USD" and base in usd_rates:
                result[pair] = 1 / usd_rates[base]

        # RUB пары
        cbr_rates = self.get_rates_cbr()
        result.update(cbr_rates)

        return result


class MultiSourceDataProvider:
    """
    Главный провайдер данных с мульти-источниками и fallback.

    Приоритеты:
    1. CCXT (KuCoin/Kraken/OKX) - для OHLCV
    2. CoinGecko - для цен и market data
    3. Forex Provider - для валютных пар
    """

    def __init__(
        self,
        coingecko_api_key: Optional[str] = None,
        twelve_data_api_key: Optional[str] = None
    ):
        self.coingecko = CoinGeckoProvider(api_key=coingecko_api_key)
        self.ccxt_provider = CCXTProvider()
        self.forex_provider = ForexProvider(twelve_data_api_key=twelve_data_api_key)

        # Кэш для OHLCV данных
        self.ohlcv_cache: Dict[str, Tuple[datetime, pd.DataFrame]] = {}
        self.ohlcv_cache_ttl = timedelta(minutes=5)

        logger.info("MultiSourceDataProvider initialized")

    def _is_forex_pair(self, symbol: str) -> bool:
        """Проверить, является ли символ Forex парой."""
        forex_currencies = ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "RUB"]
        parts = symbol.replace("/", "_").split("_")
        if len(parts) != 2:
            return False
        return parts[0] in forex_currencies and parts[1] in forex_currencies

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Получить OHLCV данные с автоматическим выбором источника.
        """
        cache_key = f"{symbol}_{timeframe}_{limit}"

        # Проверяем кэш
        if not force_refresh and cache_key in self.ohlcv_cache:
            cache_time, df = self.ohlcv_cache[cache_key]
            if datetime.now() - cache_time < self.ohlcv_cache_ttl:
                return df.copy()

        # Forex пара
        if self._is_forex_pair(symbol):
            logger.info(f"Fetching Forex data for {symbol}")
            # Для Forex у нас пока только текущие курсы, не OHLCV
            # TODO: Добавить OHLCV для Forex через Twelve Data
            return None

        # Крипто - используем CCXT
        df = self.ccxt_provider.fetch_ohlcv(symbol, timeframe, limit)

        if df is not None and not df.empty:
            self.ohlcv_cache[cache_key] = (datetime.now(), df.copy())
            return df

        # Fallback на CoinGecko (только для больших таймфреймов)
        if timeframe in ["1d", "1w"]:
            days = 30 if timeframe == "1d" else 90
            df = self.coingecko.get_ohlcv(symbol, days=days)
            if df is not None:
                self.ohlcv_cache[cache_key] = (datetime.now(), df.copy())
                return df

        return None

    def get_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Получить текущие цены для списка символов.
        """
        result = {}
        crypto_symbols = []
        forex_symbols = []

        # Разделяем символы по типам
        for s in symbols:
            if self._is_forex_pair(s):
                forex_symbols.append(s)
            else:
                crypto_symbols.append(s)

        # Крипто цены через CoinGecko
        if crypto_symbols:
            cg_prices = self.coingecko.get_price(crypto_symbols)
            result.update(cg_prices)

        # Forex курсы
        if forex_symbols:
            for pair in forex_symbols:
                rate = self.forex_provider.get_pair_rate(pair)
                if rate:
                    result[pair] = {"price": rate, "change_24h": 0, "volume_24h": 0}

        return result

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Получить тикер для символа."""
        if self._is_forex_pair(symbol):
            rate = self.forex_provider.get_pair_rate(symbol)
            if rate:
                return {
                    "symbol": symbol,
                    "last": rate,
                    "bid": rate * 0.9999,
                    "ask": rate * 1.0001,
                    "percentage": 0,
                    "baseVolume": 0,
                    "quoteVolume": 0
                }
            return None

        return self.ccxt_provider.fetch_ticker(symbol)

    def get_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """Получить тикеры для списка символов."""
        result = {}

        for symbol in symbols:
            ticker = self.get_ticker(symbol)
            if ticker:
                result[symbol] = ticker

        return result

    def get_market_overview(self) -> Dict[str, Any]:
        """Получить обзор рынка."""
        # Топ монеты через CoinGecko
        market_data = self.coingecko.get_market_data(limit=50)

        # Forex курсы
        forex_rates = self.forex_provider.get_all_rates()

        # Статус источников
        health = self.ccxt_provider.get_health_status()

        return {
            "crypto_markets": market_data,
            "forex_rates": forex_rates,
            "source_health": {k: {"is_healthy": v.is_healthy, "error_count": v.error_count} for k, v in health.items()},
            "timestamp": datetime.now().isoformat()
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Получить статус здоровья всех источников."""
        ccxt_health = self.ccxt_provider.get_health_status()

        return {
            "ccxt_exchanges": {k: v.__dict__ for k, v in ccxt_health.items()},
            "coingecko": "healthy",  # TODO: добавить health check
            "forex": "healthy",
            "timestamp": datetime.now().isoformat()
        }


# Глобальный экземпляр для удобства
_provider: Optional[MultiSourceDataProvider] = None


def get_data_provider() -> MultiSourceDataProvider:
    """Получить глобальный экземпляр провайдера."""
    global _provider
    if _provider is None:
        _provider = MultiSourceDataProvider()
    return _provider
