"""
Trading Configuration - Tier-based coin configuration for 50 pairs.
Based on quick_start_code.md and bot_polish_guide.md specifications.
"""

# TIER 1: MEGA coins (BTC, ETH, BNB, SOL, XRP) - 85% accuracy
# Trade all signals without strict filters
TIER_1 = {
    'BTC/USDT': {'min_volume_usd': 20_000_000_000, 'confidence_threshold': 40, 'position_size_percent': 3.0, 'sl_percent': 2.5},
    'ETH/USDT': {'min_volume_usd': 10_000_000_000, 'confidence_threshold': 40, 'position_size_percent': 3.0, 'sl_percent': 2.5},
    'BNB/USDT': {'min_volume_usd': 5_000_000_000, 'confidence_threshold': 40, 'position_size_percent': 3.0, 'sl_percent': 2.5},
    'SOL/USDT': {'min_volume_usd': 3_000_000_000, 'confidence_threshold': 40, 'position_size_percent': 3.0, 'sl_percent': 2.5},
    'XRP/USDT': {'min_volume_usd': 2_000_000_000, 'confidence_threshold': 40, 'position_size_percent': 3.0, 'sl_percent': 2.5},
}

# TIER 2: LARGE coins ($500M-$3B volume) - 75% accuracy
# Trade signals with confidence > 55%
TIER_2 = {
    'ADA/USDT': {'min_volume_usd': 800_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'DOGE/USDT': {'min_volume_usd': 900_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'MATIC/USDT': {'min_volume_usd': 700_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'LINK/USDT': {'min_volume_usd': 600_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'AVAX/USDT': {'min_volume_usd': 500_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'DOT/USDT': {'min_volume_usd': 500_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'SHIB/USDT': {'min_volume_usd': 1_000_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'NEAR/USDT': {'min_volume_usd': 400_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'UNI/USDT': {'min_volume_usd': 500_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'LTC/USDT': {'min_volume_usd': 400_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'TRX/USDT': {'min_volume_usd': 500_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'BCH/USDT': {'min_volume_usd': 300_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'ETC/USDT': {'min_volume_usd': 300_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'APT/USDT': {'min_volume_usd': 400_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
    'SUI/USDT': {'min_volume_usd': 500_000_000, 'confidence_threshold': 55, 'position_size_percent': 2.0, 'sl_percent': 3.0},
}

# TIER 3: MID coins ($100M-$500M volume) - 60% accuracy
# Trade ONLY signals with confidence > 70% and triple confirmation
TIER_3 = {
    'ATOM/USDT': {'min_volume_usd': 200_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'ALGO/USDT': {'min_volume_usd': 150_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'FTM/USDT': {'min_volume_usd': 150_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'AAVE/USDT': {'min_volume_usd': 300_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'ARB/USDT': {'min_volume_usd': 400_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'OP/USDT': {'min_volume_usd': 300_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'INJ/USDT': {'min_volume_usd': 120_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'ICP/USDT': {'min_volume_usd': 150_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'GALA/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'CHZ/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'LDO/USDT': {'min_volume_usd': 150_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'CRV/USDT': {'min_volume_usd': 120_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'SNX/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'COMP/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'MKR/USDT': {'min_volume_usd': 200_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'PEPE/USDT': {'min_volume_usd': 300_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'WIF/USDT': {'min_volume_usd': 200_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'BONK/USDT': {'min_volume_usd': 150_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'SAND/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'MANA/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'AXS/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'EOS/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'XLM/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'HBAR/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'FIL/USDT': {'min_volume_usd': 150_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    # Extra hot coins
    'GUN/USDT': {'min_volume_usd': 50_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.0, 'sl_percent': 5.0, 'require_triple_confirmation': True},
    'FLOKI/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'WLD/USDT': {'min_volume_usd': 150_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'RENDER/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'THETA/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'IMX/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'RUNE/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'EGLD/USDT': {'min_volume_usd': 100_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'FLOW/USDT': {'min_volume_usd': 80_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'XTZ/USDT': {'min_volume_usd': 80_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'VET/USDT': {'min_volume_usd': 80_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
    'GRT/USDT': {'min_volume_usd': 80_000_000, 'confidence_threshold': 70, 'position_size_percent': 1.5, 'sl_percent': 4.0, 'require_triple_confirmation': True},
}


# Combined config
TRADING_CONFIG = {
    'TIER_1': TIER_1,
    'TIER_2': TIER_2,
    'TIER_3': TIER_3,
}

# All pairs list (50 pairs)
ALL_PAIRS = list(TIER_1.keys()) + list(TIER_2.keys()) + list(TIER_3.keys())


def get_coin_tier(symbol: str) -> str:
    """Get tier for a symbol."""
    if symbol in TIER_1:
        return 'TIER_1'
    elif symbol in TIER_2:
        return 'TIER_2'
    elif symbol in TIER_3:
        return 'TIER_3'
    else:
        return 'UNKNOWN'


def get_coin_config(symbol: str) -> dict:
    """Get config for a symbol."""
    tier = get_coin_tier(symbol)
    if tier == 'TIER_1':
        return TIER_1.get(symbol, {})
    elif tier == 'TIER_2':
        return TIER_2.get(symbol, {})
    elif tier == 'TIER_3':
        return TIER_3.get(symbol, {})
    return {}


def get_confidence_threshold(symbol: str) -> float:
    """Get confidence threshold for a symbol."""
    config = get_coin_config(symbol)
    return config.get('confidence_threshold', 70)


def requires_triple_confirmation(symbol: str) -> bool:
    """Check if symbol requires triple confirmation (TIER_3)."""
    config = get_coin_config(symbol)
    return config.get('require_triple_confirmation', False)
