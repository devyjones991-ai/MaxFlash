"""
Сканер пар Uniswap v3.
"""
from web3 import Web3
from typing import List, Dict, Optional
import structlog
from app.config import settings

logger = structlog.get_logger()

# Uniswap V3 Factory ABI (упрощённый)
UNISWAP_V3_FACTORY_ABI = [
    {
        "inputs": [],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "allPools",
        "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V3 Pool ABI (упрощённый)
UNISWAP_V3_POOL_ABI = [
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


class UniswapV3Scanner:
    """Сканер пар Uniswap v3."""
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or settings.ETH_RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.factory_address = Web3.to_checksum_address(settings.UNISWAP_V3_FACTORY)
        self.factory_contract = self.w3.eth.contract(
            address=self.factory_address,
            abi=UNISWAP_V3_FACTORY_ABI
        )
    
    def get_pool_address(
        self,
        token0: str,
        token1: str,
        fee: int = 3000  # 0.3% fee tier
    ) -> Optional[str]:
        """
        Получить адрес пула для пары токенов.
        
        Args:
            token0: Адрес первого токена
            token1: Адрес второго токена
            fee: Fee tier (3000 = 0.3%, 500 = 0.05%, 10000 = 1%)
        """
        try:
            token0 = Web3.to_checksum_address(token0)
            token1 = Web3.to_checksum_address(token1)
            
            # Uniswap V3 использует функцию getPool
            # Но в Factory нет прямой функции, нужно использовать другой подход
            # Для MVP используем упрощённый метод через события или внешние API
            
            logger.warning("Direct pool address lookup not implemented, using fallback")
            return None
        except Exception as e:
            logger.error("Error getting pool address", error=str(e))
            return None
    
    def get_pool_info(self, pool_address: str) -> Optional[Dict]:
        """Получить информацию о пуле."""
        try:
            pool_address = Web3.to_checksum_address(pool_address)
            pool_contract = self.w3.eth.contract(
                address=pool_address,
                abi=UNISWAP_V3_POOL_ABI
            )
            
            token0 = pool_contract.functions.token0().call()
            token1 = pool_contract.functions.token1().call()
            liquidity = pool_contract.functions.liquidity().call()
            slot0 = pool_contract.functions.slot0().call()
            
            return {
                "pool_address": pool_address,
                "token0": token0,
                "token1": token1,
                "liquidity": liquidity,
                "sqrt_price_x96": slot0[0],
                "tick": slot0[1],
            }
        except Exception as e:
            logger.error("Error getting pool info", pool=pool_address, error=str(e))
            return None
    
    def scan_new_pairs(self, limit: int = 100) -> List[Dict]:
        """
        Сканировать новые пары (заглушка).
        В реальности нужно слушать события PairCreated или использовать TheGraph.
        """
        logger.info("Scanning new pairs", limit=limit)
        # TODO: реализовать через события или TheGraph API
        return []

