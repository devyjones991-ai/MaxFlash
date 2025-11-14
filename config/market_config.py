"""
Конфигурация для мульти-рыночного анализа.
Настройки бирж, секторная классификация, rate limits.
"""
from typing import Dict, List

# Приоритетные биржи для быстрого доступа
PRIORITY_EXCHANGES = [
    'binance', 'okx', 'bybit', 'gate', 'kraken',
    'bitget', 'bingx', 'htx', 'bitmart', 'coinbase'
]

# Rate limits для разных бирж (запросов в секунду)
EXCHANGE_RATE_LIMITS: Dict[str, float] = {
    'binance': 10.0,
    'okx': 20.0,
    'bybit': 10.0,
    'gate': 10.0,
    'kraken': 1.0,
    'bitget': 10.0,
    'bingx': 10.0,
    'htx': 10.0,
    'bitmart': 10.0,
    'coinbase': 10.0,
}

# Секторная классификация криптовалют
SECTOR_CLASSIFICATION: Dict[str, List[str]] = {
    'Layer 1': [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT',
        'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT',
        'ATOM/USDT', 'NEAR/USDT', 'ALGO/USDT', 'FTM/USDT',
        'ICP/USDT', 'APT/USDT', 'SUI/USDT', 'ARB/USDT',
        'OP/USDT', 'INJ/USDT', 'TIA/USDT', 'SEI/USDT'
    ],
    'Layer 2': [
        'ARB/USDT', 'OP/USDT', 'MATIC/USDT', 'IMX/USDT',
        'METIS/USDT', 'BOBA/USDT', 'LRC/USDT', 'DYDX/USDT'
    ],
    'DeFi': [
        'UNI/USDT', 'AAVE/USDT', 'COMP/USDT', 'MKR/USDT',
        'SUSHI/USDT', 'CRV/USDT', 'SNX/USDT', 'YFI/USDT',
        '1INCH/USDT', 'BAL/USDT', 'CAKE/USDT', 'PancakeSwap',
        'GMX/USDT', 'RDNT/USDT', 'MAGIC/USDT', 'GNS/USDT'
    ],
    'NFT & Gaming': [
        'AXS/USDT', 'SAND/USDT', 'MANA/USDT', 'ENJ/USDT',
        'GALA/USDT', 'IMX/USDT', 'APE/USDT', 'GMT/USDT',
        'MAGIC/USDT', 'YGG/USDT', 'ILV/USDT', 'ALICE/USDT'
    ],
    'Exchange Tokens': [
        'BNB/USDT', 'FTT/USDT', 'HT/USDT', 'OKB/USDT',
        'KCS/USDT', 'GT/USDT', 'CRO/USDT', 'LEO/USDT'
    ],
    'Meme Coins': [
        'DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT',
        'BONK/USDT', 'WIF/USDT', 'BOME/USDT', 'MYRO/USDT'
    ],
    'AI & Big Data': [
        'FET/USDT', 'AGIX/USDT', 'OCEAN/USDT', 'RNDR/USDT',
        'TAO/USDT', 'AI/USDT', 'ARKM/USDT', 'NMR/USDT'
    ],
    'Privacy': [
        'XMR/USDT', 'ZEC/USDT', 'DASH/USDT', 'ZEN/USDT'
    ],
    'Stablecoins': [
        'USDT/USDT', 'USDC/USDT', 'DAI/USDT', 'BUSD/USDT',
        'TUSD/USDT', 'USDP/USDT', 'USDD/USDT'
    ],
    'Oracle': [
        'LINK/USDT', 'BAND/USDT', 'API3/USDT', 'UMA/USDT',
        'DIA/USDT', 'TRB/USDT', 'PENDLE/USDT'
    ],
    'Metaverse': [
        'SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'ENJ/USDT',
        'GALA/USDT', 'TLM/USDT', 'CHR/USDT', 'ALICE/USDT'
    ],
    'Storage': [
        'FIL/USDT', 'AR/USDT', 'STORJ/USDT', 'SIA/USDT'
    ],
    'Social': [
        'LENS/USDT', 'GAL/USDT', 'RSS3/USDT', 'MASK/USDT'
    ]
}

# Популярные торговые пары для быстрого доступа
POPULAR_PAIRS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT',
    'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT',
    'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'UNI/USDT',
    'ATOM/USDT', 'LTC/USDT', 'NEAR/USDT', 'ALGO/USDT',
    'FTM/USDT', 'ICP/USDT', 'APT/USDT', 'ARB/USDT'
]

# Настройки кэширования
CACHE_CONFIG = {
    'ohlcv_ttl_minutes': 5,
    'ticker_ttl_minutes': 1,
    'markets_ttl_minutes': 30,
    'stats_ttl_minutes': 5
}

# Настройки для batch загрузки
BATCH_CONFIG = {
    'max_workers': 5,
    'delay_between_requests': 0.1,  # секунды
    'max_pairs_per_batch': 100
}

# Настройки для Market Overview
MARKET_OVERVIEW_CONFIG = {
    'top_pairs_count': 100,
    'heatmap_resolution': '1h',  # Таймфрейм для heatmap
    'update_interval_seconds': 60
}

# Настройки для корреляционного анализа
CORRELATION_CONFIG = {
    'min_data_points': 100,
    'correlation_period_days': 30,
    'min_correlation_threshold': 0.5
}

def get_sector_for_pair(pair: str) -> Optional[str]:
    """
    Получить сектор для торговой пары.

    Args:
        pair: Торговая пара (например, 'BTC/USDT')

    Returns:
        Название сектора или None
    """
    for sector, pairs in SECTOR_CLASSIFICATION.items():
        if pair in pairs:
            return sector
    return None

def get_all_sectors() -> List[str]:
    """Получить список всех секторов."""
    return list(SECTOR_CLASSIFICATION.keys())

def get_pairs_by_sector(sector: str) -> List[str]:
    """
    Получить список пар для сектора.

    Args:
        sector: Название сектора

    Returns:
        Список торговых пар
    """
    return SECTOR_CLASSIFICATION.get(sector, [])

