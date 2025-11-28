"""
Тесты для детектора скама.
"""
import pytest
from services.scam_detector.rule_based_detector import RuleBasedScamDetector


def test_rule_based_detector_safe_token():
    """Тест детектора для безопасного токена."""
    detector = RuleBasedScamDetector()
    
    features = {
        "is_proxy": False,
        "is_upgradeable": False,
        "has_blacklist": False,
        "has_mint": False,
        "tax_buy_percent": 0.0,
        "tax_sell_percent": 0.0,
        "total_liquidity_usd": 100000.0,
        "lp_locked": True,
        "lp_lock_percent": 100.0,
        "volume_24h_usd": 50000.0,
        "buy_sell_ratio": 1.0,
    }
    
    result = detector.detect(features)
    
    assert result["scam_score"] < 0.4
    assert result["scam_class"] in ["safe", "low_risk"]


def test_rule_based_detector_scam_token():
    """Тест детектора для скам токена."""
    detector = RuleBasedScamDetector()
    
    features = {
        "is_proxy": True,
        "is_upgradeable": True,
        "has_blacklist": True,
        "has_mint": True,
        "tax_buy_percent": 0.0,
        "tax_sell_percent": 20.0,  # Высокий sell tax
        "total_liquidity_usd": 1000.0,  # Низкая ликвидность
        "lp_locked": False,
        "lp_lock_percent": 0.0,
        "volume_24h_usd": 0.0,
        "buy_sell_ratio": 100.0,  # Подозрительное соотношение
    }
    
    result = detector.detect(features)
    
    assert result["scam_score"] >= 0.7
    assert result["scam_class"] in ["high_risk", "scam"]
    assert len(result["reasons"]) > 0

