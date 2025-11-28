"""
Извлечение фич для детекции скама.
"""
from web3 import Web3
from typing import Dict, Optional, List
import structlog
from app.config import settings

logger = structlog.get_logger()

# ERC20 ABI (базовый)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]


class ScamFeatureExtractor:
    """Извлечение фич для детекции скама."""
    
    def __init__(self, rpc_url: str, chain: str):
        self.rpc_url = rpc_url
        self.chain = chain
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    async def extract_contract_features(
        self,
        token_address: str
    ) -> Dict:
        """
        Извлечь фичи контракта токена.
        
        Returns:
            Словарь с фичами контракта
        """
        features = {
            "is_proxy": False,
            "is_upgradeable": False,
            "has_blacklist": False,
            "has_whitelist": False,
            "has_mint": False,
            "has_pause": False,
            "tax_buy_percent": 0.0,
            "tax_sell_percent": 0.0,
            "owner_address": None,
            "is_owner_renounced": False,
        }
        
        try:
            token_address = Web3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(
                address=token_address,
                abi=ERC20_ABI
            )
            
            # Проверка на прокси (упрощённая)
            code = self.w3.eth.get_code(token_address)
            if len(code) > 0:
                # Проверяем наличие delegatecall (признак прокси)
                if b'\x36\x3d\x3d\x37\x3d' in code or b'delegatecall' in code.hex():
                    features["is_proxy"] = True
            
            # Проверка на upgradeable (упрощённая)
            # В реальности нужно проверять наличие функций upgrade/upgradeTo
            try:
                # Попытка вызвать функцию owner() (стандарт OpenZeppelin)
                owner_func = token_contract.functions.owner()
                owner_address = owner_func.call()
                features["owner_address"] = owner_address
                
                # Проверка на renounced ownership (нулевой адрес)
                if owner_address == "0x0000000000000000000000000000000000000000":
                    features["is_owner_renounced"] = True
            except:
                pass
            
            # Проверка на blacklist/whitelist (упрощённая)
            # В реальности нужно проверять наличие функций isBlacklisted/isWhitelisted
            try:
                # Попытка вызвать функцию isBlacklisted
                blacklist_func = token_contract.functions.isBlacklisted("0x0000000000000000000000000000000000000000")
                blacklist_func.call()
                features["has_blacklist"] = True
            except:
                pass
            
            # Проверка на mint (упрощённая)
            try:
                mint_func = token_contract.functions.mint("0x0000000000000000000000000000000000000000", 0)
                mint_func.call()
                features["has_mint"] = True
            except:
                pass
            
            # Проверка на pause (упрощённая)
            try:
                pause_func = token_contract.functions.paused()
                pause_func.call()
                features["has_pause"] = True
            except:
                pass
            
            logger.info("Extracted contract features", token=token_address, features=features)
            
        except Exception as e:
            logger.error("Error extracting contract features", token=token_address, error=str(e))
        
        return features
    
    async def extract_liquidity_features(
        self,
        pools: List[Dict]
    ) -> Dict:
        """
        Извлечь фичи ликвидности из пулов.
        
        Args:
            pools: Список пулов токена
        """
        features = {
            "total_liquidity_usd": 0.0,
            "pool_count": len(pools),
            "lp_locked": False,
            "lp_lock_percent": 0.0,
            "largest_pool_liquidity_usd": 0.0,
        }
        
        if not pools:
            return features
        
        total_liquidity = 0.0
        largest_liquidity = 0.0
        
        for pool in pools:
            liquidity_usd = float(pool.get("liquidity_usd", 0) or 0)
            total_liquidity += liquidity_usd
            largest_liquidity = max(largest_liquidity, liquidity_usd)
            
            # Проверка на блокировку LP (упрощённая)
            if pool.get("lp_locked", False):
                features["lp_locked"] = True
                features["lp_lock_percent"] = max(
                    features["lp_lock_percent"],
                    float(pool.get("lp_lock_percent", 0) or 0)
                )
        
        features["total_liquidity_usd"] = total_liquidity
        features["largest_pool_liquidity_usd"] = largest_liquidity
        
        return features
    
    async def extract_trading_features(
        self,
        pools: List[Dict]
    ) -> Dict:
        """
        Извлечь фичи торговой активности.
        
        Args:
            pools: Список пулов токена
        """
        features = {
            "volume_24h_usd": 0.0,
            "transactions_24h": 0,
            "unique_buyers_24h": 0,
            "unique_sellers_24h": 0,
            "buy_sell_ratio": 0.0,
        }
        
        if not pools:
            return features
        
        total_volume = 0.0
        total_transactions = 0
        total_buyers = 0
        total_sellers = 0
        
        for pool in pools:
            total_volume += float(pool.get("volume_24h_usd", 0) or 0)
            total_transactions += int(pool.get("transactions_24h", 0) or 0)
            total_buyers += int(pool.get("unique_buyers_24h", 0) or 0)
            total_sellers += int(pool.get("unique_sellers_24h", 0) or 0)
        
        features["volume_24h_usd"] = total_volume
        features["transactions_24h"] = total_transactions
        features["unique_buyers_24h"] = total_buyers
        features["unique_sellers_24h"] = total_sellers
        
        if total_sellers > 0:
            features["buy_sell_ratio"] = total_buyers / total_sellers
        
        return features
    
    async def extract_all_features(
        self,
        token_address: str,
        pools: List[Dict]
    ) -> Dict:
        """
        Извлечь все фичи токена.
        
        Args:
            token_address: Адрес токена
            pools: Список пулов токена
        """
        contract_features = await self.extract_contract_features(token_address)
        liquidity_features = await self.extract_liquidity_features(pools)
        trading_features = await self.extract_trading_features(pools)
        
        all_features = {
            **contract_features,
            **liquidity_features,
            **trading_features,
        }
        
        return all_features

