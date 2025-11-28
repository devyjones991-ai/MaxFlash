"""
Сервис сканирования DEX для поиска новых токенов и пулов.
"""
from typing import List, Dict, Optional
import structlog
from datetime import datetime

from services.dex_ingest.uniswap_scanner import UniswapV3Scanner
from services.dex_ingest.pancakeswap_scanner import PancakeSwapScanner
from app.repositories.token_repository import TokenRepository
from app.database import AsyncSession

logger = structlog.get_logger()


class DEXScannerService:
    """Сервис сканирования DEX."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.uniswap_scanner = UniswapV3Scanner()
        self.pancakeswap_scanner = PancakeSwapScanner()
        self.token_repo = TokenRepository(db)
    
    async def scan_uniswap_pools(
        self,
        token_address: str,
        weth_address: str = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    ) -> List[Dict]:
        """
        Сканировать пулы Uniswap v3 для токена.
        
        Args:
            token_address: Адрес токена
            weth_address: Адрес WETH
        """
        logger.info("Scanning Uniswap pools", token=token_address)
        
        pools = []
        # Проверяем разные fee tiers
        for fee in [500, 3000, 10000]:  # 0.05%, 0.3%, 1%
            pool_address = self.uniswap_scanner.get_pool_address(
                token_address,
                weth_address,
                fee
            )
            
            if pool_address:
                pool_info = self.uniswap_scanner.get_pool_info(pool_address)
                if pool_info:
                    pool_info["fee"] = fee
                    pools.append(pool_info)
        
        return pools
    
    async def scan_pancakeswap_pairs(
        self,
        token_address: str
    ) -> List[Dict]:
        """
        Сканировать пары PancakeSwap для токена.
        
        Args:
            token_address: Адрес токена
        """
        logger.info("Scanning PancakeSwap pairs", token=token_address)
        
        pairs = []
        # Ищем пару с WBNB
        pair_address = self.pancakeswap_scanner.get_pair_address(
            token_address,
            self.pancakeswap_scanner.WBNB
        )
        
        if pair_address:
            pair_info = self.pancakeswap_scanner.get_pair_info(pair_address)
            if pair_info:
                pairs.append(pair_info)
        
        return pairs
    
    async def ingest_token_pools(
        self,
        token_address: str,
        chain: str
    ) -> List[Dict]:
        """
        Инжестить пулы токена в БД.
        
        Args:
            token_address: Адрес токена
            chain: 'ethereum' или 'bsc'
        """
        logger.info("Ingesting token pools", token=token_address, chain=chain)
        
        # Получаем или создаём токен
        token = await self.token_repo.get_by_address(token_address, chain)
        
        if not token:
            # Создаём новый токен (базовая информация)
            token = await self.token_repo.create({
                "address": token_address.lower(),
                "chain": chain,
                "symbol": "UNKNOWN",  # Будет обновлено позже
                "name": "Unknown Token",
            })
        
        pools_data = []
        
        if chain == "ethereum":
            pools = await self.scan_uniswap_pools(token_address)
            for pool in pools:
                pool_data = {
                    "token_id": token.id,
                    "dex": "uniswap_v3",
                    "pool_address": pool["pool_address"].lower(),
                    "token0_address": pool["token0"].lower(),
                    "token1_address": pool["token1"].lower(),
                    "reserve0": str(pool.get("liquidity", 0)),
                    "reserve1": "0",  # Для v3 нужно рассчитывать отдельно
                }
                pools_data.append(pool_data)
        
        elif chain == "bsc":
            pairs = await self.scan_pancakeswap_pairs(token_address)
            for pair in pairs:
                pool_data = {
                    "token_id": token.id,
                    "dex": "pancakeswap",
                    "pool_address": pair["pair_address"].lower(),
                    "pair_address": pair["pair_address"].lower(),
                    "token0_address": pair["token0"].lower(),
                    "token1_address": pair["token1"].lower(),
                    "reserve0": str(pair["reserve0"]),
                    "reserve1": str(pair["reserve1"]),
                }
                pools_data.append(pool_data)
        
        # Сохраняем пулы
        created_pools = []
        for pool_data in pools_data:
            # Проверяем, существует ли уже пул
            existing_pools = await self.token_repo.get_pools_by_token(token.id)
            pool_exists = any(
                p.pool_address == pool_data["pool_address"]
                for p in existing_pools
            )
            
            if not pool_exists:
                pool = await self.token_repo.create_pool(pool_data)
                created_pools.append(pool)
        
        logger.info(
            "Ingested pools",
            token=token_address,
            pools_created=len(created_pools)
        )
        
        return [{"pool_address": p.pool_address, "dex": p.dex} for p in created_pools]

