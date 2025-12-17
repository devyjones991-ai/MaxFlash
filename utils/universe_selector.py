"""
Universe Selector for Top-N Crypto Pairs.

Selects top pairs by aggregated volume across multiple exchanges (Binance, Bybit, OKX).
Ensures pairs are available on at least 2 out of 3 exchanges for reliability.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from utils.exchange_manager import ExchangeManager
from utils.logger_config import setup_logging

logger = setup_logging()


class UniverseSelector:
    """
    Selects top trading pairs by aggregated volume across multiple exchanges.
    
    Features:
    - Fetches tickers from Binance, Bybit, OKX
    - Aggregates volume using median (robust to outliers)
    - Filters pairs available on at least min_exchanges
    - Returns top-N pairs sorted by volume
    - Caches results for performance
    """
    
    # Target exchanges for multi-exchange strategy
    TARGET_EXCHANGES = ["binance", "bybit", "okx"]
    
    # Minimum volume threshold (USD) to filter out illiquid pairs
    MIN_VOLUME_USD = 10_000_000  # $10M daily volume minimum
    
    # Stablecoins and wrapped tokens to exclude
    EXCLUDED_BASES = {
        "USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP", "USDD", "FDUSD",
        "WBTC", "WETH", "STETH", "CBETH", "RETH",
        "EUR", "GBP", "AUD", "TRY", "BRL", "RUB",
    }
    
    def __init__(
        self,
        exchange_manager: Optional[ExchangeManager] = None,
        min_exchanges: int = 2,
        cache_ttl_minutes: int = 30,
    ):
        """
        Initialize Universe Selector.
        
        Args:
            exchange_manager: ExchangeManager instance (creates new if None)
            min_exchanges: Minimum number of exchanges where pair must be available
            cache_ttl_minutes: Cache TTL in minutes
        """
        self.exchange_manager = exchange_manager or ExchangeManager()
        self.min_exchanges = min_exchanges
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        
        # Cache
        self._cached_universe: List[Dict] = []
        self._cache_time: Optional[datetime] = None
    
    def _fetch_all_tickers(self) -> Dict[str, Dict[str, Dict]]:
        """
        Fetch tickers from all target exchanges.
        
        Returns:
            Dict[exchange_id, Dict[symbol, ticker_data]]
        """
        all_tickers = {}
        
        for exchange_id in self.TARGET_EXCHANGES:
            try:
                exchange = self.exchange_manager.get_exchange_instance(exchange_id)
                if not exchange:
                    logger.warning(f"Exchange {exchange_id} not available")
                    continue
                
                # Fetch all tickers at once (more efficient)
                tickers = exchange.fetch_tickers()
                
                # Filter USDT pairs only
                usdt_tickers = {
                    symbol: ticker
                    for symbol, ticker in tickers.items()
                    if symbol.endswith("/USDT") and ticker.get("quoteVolume")
                }
                
                all_tickers[exchange_id] = usdt_tickers
                logger.info(f"Fetched {len(usdt_tickers)} USDT tickers from {exchange_id}")
                
            except Exception as e:
                logger.error(f"Failed to fetch tickers from {exchange_id}: {e}")
                all_tickers[exchange_id] = {}
        
        return all_tickers
    
    def _aggregate_volumes(
        self, 
        all_tickers: Dict[str, Dict[str, Dict]]
    ) -> Dict[str, Dict]:
        """
        Aggregate volumes across exchanges for each symbol.
        
        Uses median volume (robust to outliers from different exchange reporting).
        
        Args:
            all_tickers: Tickers from all exchanges
            
        Returns:
            Dict[symbol, {volume, exchanges, prices, best_exchange}]
        """
        # Collect data per symbol
        symbol_data = defaultdict(lambda: {
            "volumes": [],
            "prices": [],
            "exchanges": [],
            "tickers": {},
        })
        
        for exchange_id, tickers in all_tickers.items():
            for symbol, ticker in tickers.items():
                # Extract base currency
                base = symbol.split("/")[0]
                
                # Skip excluded tokens
                if base in self.EXCLUDED_BASES:
                    continue
                
                volume = ticker.get("quoteVolume", 0) or 0
                price = ticker.get("last", 0) or 0
                
                if volume > 0 and price > 0:
                    symbol_data[symbol]["volumes"].append(volume)
                    symbol_data[symbol]["prices"].append(price)
                    symbol_data[symbol]["exchanges"].append(exchange_id)
                    symbol_data[symbol]["tickers"][exchange_id] = ticker
        
        # Aggregate
        aggregated = {}
        
        for symbol, data in symbol_data.items():
            if len(data["exchanges"]) < self.min_exchanges:
                continue
            
            volumes = data["volumes"]
            prices = data["prices"]
            
            # Use median for robustness
            median_volume = float(np.median(volumes))
            median_price = float(np.median(prices))
            
            # Skip low volume pairs
            if median_volume < self.MIN_VOLUME_USD:
                continue
            
            # Find best exchange (highest volume)
            best_idx = np.argmax(volumes)
            best_exchange = data["exchanges"][best_idx]
            
            aggregated[symbol] = {
                "symbol": symbol,
                "median_volume": median_volume,
                "median_price": median_price,
                "total_volume": sum(volumes),
                "exchange_count": len(data["exchanges"]),
                "exchanges": data["exchanges"],
                "best_exchange": best_exchange,
                "volumes_by_exchange": dict(zip(data["exchanges"], volumes)),
                "prices_by_exchange": dict(zip(data["exchanges"], prices)),
            }
        
        return aggregated
    
    def get_top_pairs(
        self,
        n: int = 20,
        force_refresh: bool = False,
    ) -> List[Dict]:
        """
        Get top-N pairs by aggregated volume.
        
        Args:
            n: Number of pairs to return
            force_refresh: Force refresh cache
            
        Returns:
            List of dicts with pair info, sorted by volume descending
        """
        # Check cache
        if not force_refresh and self._cached_universe and self._cache_time:
            if datetime.now() - self._cache_time < self.cache_ttl:
                logger.debug("Returning cached universe")
                return self._cached_universe[:n]
        
        logger.info(f"Refreshing universe (top-{n} pairs across {self.TARGET_EXCHANGES})")
        
        # Fetch and aggregate
        all_tickers = self._fetch_all_tickers()
        aggregated = self._aggregate_volumes(all_tickers)
        
        # Sort by median volume descending
        sorted_pairs = sorted(
            aggregated.values(),
            key=lambda x: x["median_volume"],
            reverse=True,
        )
        
        # Cache results
        self._cached_universe = sorted_pairs
        self._cache_time = datetime.now()
        
        logger.info(f"Universe refreshed: {len(sorted_pairs)} pairs total, returning top {n}")
        
        # Log top pairs for debugging
        for i, pair in enumerate(sorted_pairs[:n], 1):
            logger.debug(
                f"  {i:2d}. {pair['symbol']:12s} | "
                f"Vol: ${pair['median_volume']/1e6:>8.1f}M | "
                f"Exchanges: {pair['exchange_count']} ({', '.join(pair['exchanges'])})"
            )
        
        return sorted_pairs[:n]
    
    def get_pair_symbols(self, n: int = 20, force_refresh: bool = False) -> List[str]:
        """
        Get just the symbol names for top-N pairs.
        
        Args:
            n: Number of pairs
            force_refresh: Force cache refresh
            
        Returns:
            List of symbol strings (e.g., ["BTC/USDT", "ETH/USDT", ...])
        """
        pairs = self.get_top_pairs(n=n, force_refresh=force_refresh)
        return [p["symbol"] for p in pairs]
    
    def get_best_exchange_for_symbol(self, symbol: str) -> str:
        """
        Get the best exchange (highest volume) for a specific symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Exchange ID (defaults to 'binance' if not found)
        """
        # Use cached data if available
        if self._cached_universe:
            for pair in self._cached_universe:
                if pair["symbol"] == symbol:
                    return pair["best_exchange"]
        
        # Fallback to binance
        return "binance"
    
    def get_available_exchanges_for_symbol(self, symbol: str) -> List[str]:
        """
        Get list of exchanges where symbol is available.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of exchange IDs
        """
        if self._cached_universe:
            for pair in self._cached_universe:
                if pair["symbol"] == symbol:
                    return pair["exchanges"]
        
        return ["binance"]  # Fallback
    
    def is_symbol_in_universe(self, symbol: str, n: int = 20) -> bool:
        """
        Check if symbol is in top-N universe.
        
        Args:
            symbol: Trading pair symbol
            n: Universe size
            
        Returns:
            True if symbol is in top-N
        """
        top_symbols = self.get_pair_symbols(n=n)
        return symbol in top_symbols


# Singleton instance
_universe_selector: Optional[UniverseSelector] = None


def get_universe_selector() -> UniverseSelector:
    """Get or create UniverseSelector singleton."""
    global _universe_selector
    if _universe_selector is None:
        _universe_selector = UniverseSelector()
    return _universe_selector


def get_top_20_pairs(force_refresh: bool = False) -> List[str]:
    """
    Convenience function to get top-20 pairs.
    
    Returns:
        List of top-20 symbol strings
    """
    selector = get_universe_selector()
    return selector.get_pair_symbols(n=20, force_refresh=force_refresh)


def get_top_n_pairs(n: int, force_refresh: bool = False) -> List[str]:
    """
    Convenience function to get top-N pairs.
    
    Args:
        n: Number of pairs
        force_refresh: Force cache refresh
        
    Returns:
        List of top-N symbol strings
    """
    selector = get_universe_selector()
    return selector.get_pair_symbols(n=n, force_refresh=force_refresh)


if __name__ == "__main__":
    # Test the selector
    print("=" * 60)
    print("UNIVERSE SELECTOR TEST")
    print("=" * 60)
    
    selector = UniverseSelector()
    
    print("\nFetching top-20 pairs by volume across Binance+Bybit+OKX...")
    top_pairs = selector.get_top_pairs(n=20)
    
    print(f"\nTop 20 pairs (available on 2+ exchanges):\n")
    print(f"{'#':>3} {'Symbol':12} {'Volume (24h)':>15} {'Price':>12} {'Exchanges':>10}")
    print("-" * 60)
    
    for i, pair in enumerate(top_pairs, 1):
        vol_str = f"${pair['median_volume']/1e9:.2f}B" if pair['median_volume'] >= 1e9 else f"${pair['median_volume']/1e6:.1f}M"
        print(
            f"{i:>3} {pair['symbol']:12} {vol_str:>15} "
            f"${pair['median_price']:>10,.2f} {pair['exchange_count']:>10}"
        )
    
    print("\n" + "=" * 60)
    print("Best exchange per symbol:")
    for pair in top_pairs[:5]:
        print(f"  {pair['symbol']}: {pair['best_exchange']}")

