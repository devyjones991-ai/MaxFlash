"""
Клиент для DexScreener API (fallback для получения данных о пулах).
"""
import httpx
from typing import List, Dict, Optional
import structlog
from app.config import settings

logger = structlog.get_logger()


class DexScreenerClient:
    """Клиент для DexScreener API."""
    
    def __init__(self):
        self.base_url = settings.DEXSCREENER_API_URL
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def get_token_pairs(
        self,
        chain: str,
        token_address: str
    ) -> List[Dict]:
        """
        Получить пары токена через DexScreener.
        
        Args:
            chain: 'ethereum' или 'bsc'
            token_address: Адрес токена
        """
        try:
            chain_id = "ethereum" if chain == "ethereum" else "bsc"
            url = f"{self.base_url}/tokens/{token_address}"
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            pairs = data.get("pairs", [])
            
            # Фильтруем по нужной сети
            filtered_pairs = [
                p for p in pairs
                if p.get("chainId") == chain_id
            ]
            
            logger.info(
                "Fetched pairs from DexScreener",
                token=token_address,
                chain=chain,
                pairs_count=len(filtered_pairs)
            )
            
            return filtered_pairs
        except Exception as e:
            logger.error(
                "Error fetching pairs from DexScreener",
                token=token_address,
                error=str(e)
            )
            return []
    
    async def get_pair_info(
        self,
        chain: str,
        pair_address: str
    ) -> Optional[Dict]:
        """
        Получить информацию о паре через DexScreener.
        
        Args:
            chain: 'ethereum' или 'bsc'
            pair_address: Адрес пары
        """
        try:
            chain_id = "ethereum" if chain == "ethereum" else "bsc"
            url = f"{self.base_url}/pairs/{chain_id}/{pair_address}"
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            pair = data.get("pair", {})
            
            return {
                "pair_address": pair.get("pairAddress"),
                "dex": pair.get("dexId"),
                "token0": {
                    "address": pair.get("baseToken", {}).get("address"),
                    "symbol": pair.get("baseToken", {}).get("symbol"),
                },
                "token1": {
                    "address": pair.get("quoteToken", {}).get("address"),
                    "symbol": pair.get("quoteToken", {}).get("symbol"),
                },
                "liquidity_usd": pair.get("liquidity", {}).get("usd"),
                "volume_24h_usd": pair.get("volume", {}).get("h24"),
                "price_usd": pair.get("priceUsd"),
                "price_change_24h": pair.get("priceChange", {}).get("h24"),
            }
        except Exception as e:
            logger.error(
                "Error fetching pair info from DexScreener",
                pair=pair_address,
                error=str(e)
            )
            return None
    
    async def close(self):
        """Закрыть HTTP клиент."""
        await self.client.aclose()

