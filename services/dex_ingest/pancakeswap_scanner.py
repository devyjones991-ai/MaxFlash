"""
Сканер пар PancakeSwap.
"""
from web3 import Web3
from typing import List, Dict, Optional
import structlog
from app.config import settings

logger = structlog.get_logger()

# PancakeSwap Factory ABI (упрощённый)
PANCAKESWAP_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "allPairs",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "allPairsLength",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# PancakeSwap Pair ABI (упрощённый)
PANCAKESWAP_PAIR_ABI = [
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
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class PancakeSwapScanner:
    """Сканер пар PancakeSwap."""
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or settings.BSC_RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.factory_address = Web3.to_checksum_address(settings.PANCAKESWAP_FACTORY)
        self.factory_contract = self.w3.eth.contract(
            address=self.factory_address,
            abi=PANCAKESWAP_FACTORY_ABI
        )
        # WBNB на BSC
        self.WBNB = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
    
    def get_pair_address(
        self,
        token0: str,
        token1: str
    ) -> Optional[str]:
        """
        Получить адрес пары для двух токенов.
        
        Args:
            token0: Адрес первого токена
            token1: Адрес второго токена
        """
        try:
            token0 = Web3.to_checksum_address(token0)
            token1 = Web3.to_checksum_address(token1)
            
            pair_address = self.factory_contract.functions.getPair(token0, token1).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
            
            return pair_address
        except Exception as e:
            logger.error("Error getting pair address", error=str(e))
            return None
    
    def get_pair_info(self, pair_address: str) -> Optional[Dict]:
        """Получить информацию о паре."""
        try:
            pair_address = Web3.to_checksum_address(pair_address)
            pair_contract = self.w3.eth.contract(
                address=pair_address,
                abi=PANCAKESWAP_PAIR_ABI
            )
            
            token0 = pair_contract.functions.token0().call()
            token1 = pair_contract.functions.token1().call()
            reserves = pair_contract.functions.getReserves().call()
            total_supply = pair_contract.functions.totalSupply().call()
            
            return {
                "pair_address": pair_address,
                "token0": token0,
                "token1": token1,
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "total_supply": total_supply,
            }
        except Exception as e:
            logger.error("Error getting pair info", pair=pair_address, error=str(e))
            return None
    
    def get_all_pairs_count(self) -> int:
        """Получить общее количество пар."""
        try:
            return self.factory_contract.functions.allPairsLength().call()
        except Exception as e:
            logger.error("Error getting pairs count", error=str(e))
            return 0
    
    def scan_recent_pairs(self, limit: int = 100) -> List[Dict]:
        """
        Сканировать недавние пары.
        
        Args:
            limit: Максимальное количество пар для сканирования
        """
        try:
            total_pairs = self.get_all_pairs_count()
            if total_pairs == 0:
                return []
            
            # Берём последние N пар
            start_index = max(0, total_pairs - limit)
            pairs = []
            
            for i in range(start_index, total_pairs):
                try:
                    pair_address = self.factory_contract.functions.allPairs(i).call()
                    pair_info = self.get_pair_info(pair_address)
                    if pair_info:
                        pairs.append(pair_info)
                except Exception as e:
                    logger.warning("Error scanning pair", index=i, error=str(e))
                    continue
            
            logger.info("Scanned pairs", count=len(pairs), total=total_pairs)
            return pairs
        except Exception as e:
            logger.error("Error scanning recent pairs", error=str(e))
            return []

