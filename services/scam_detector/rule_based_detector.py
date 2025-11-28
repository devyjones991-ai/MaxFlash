"""
Rule-based детектор скама (baseline).
"""
from typing import Dict, List
import structlog
from app.config import settings

logger = structlog.get_logger()


class RuleBasedScamDetector:
    """Rule-based детектор скама."""
    
    def __init__(self):
        self.high_risk_threshold = settings.SCAM_SCORE_THRESHOLD_HIGH
        self.medium_risk_threshold = settings.SCAM_SCORE_THRESHOLD_MEDIUM
    
    def detect(self, features: Dict) -> Dict:
        """
        Определить скам на основе правил.
        
        Args:
            features: Словарь с фичами токена
        
        Returns:
            Словарь с результатами детекции:
            - scam_score: 0.0 - 1.0
            - scam_class: 'safe', 'low_risk', 'medium_risk', 'high_risk', 'scam'
            - reasons: список причин
        """
        reasons = []
        risk_score = 0.0
        
        # Проверка контракта
        if features.get("is_proxy", False):
            risk_score += 0.1
            reasons.append("Token uses proxy contract")
        
        if features.get("is_upgradeable", False):
            risk_score += 0.15
            reasons.append("Token contract is upgradeable")
        
        if features.get("has_blacklist", False):
            risk_score += 0.2
            reasons.append("Token has blacklist function")
        
        if features.get("has_whitelist", False):
            risk_score += 0.15
            reasons.append("Token has whitelist function")
        
        if features.get("has_mint", False):
            risk_score += 0.25
            reasons.append("Token has mint function (infinite supply risk)")
        
        if features.get("has_pause", False):
            risk_score += 0.1
            reasons.append("Token has pause function")
        
        # Проверка налогов
        tax_buy = features.get("tax_buy_percent", 0.0) or 0.0
        tax_sell = features.get("tax_sell_percent", 0.0) or 0.0
        
        if tax_buy > 5.0:
            risk_score += 0.15
            reasons.append(f"High buy tax: {tax_buy}%")
        
        if tax_sell > 5.0:
            risk_score += 0.2
            reasons.append(f"High sell tax: {tax_sell}%")
        
        if tax_sell > tax_buy * 2:
            risk_score += 0.15
            reasons.append("Sell tax significantly higher than buy tax")
        
        # Проверка ownership
        if not features.get("is_owner_renounced", False):
            risk_score += 0.05
            reasons.append("Token owner not renounced")
        
        # Проверка ликвидности
        total_liquidity = features.get("total_liquidity_usd", 0.0) or 0.0
        min_liquidity = settings.MIN_LIQUIDITY_USD
        
        if total_liquidity < min_liquidity:
            risk_score += 0.3
            reasons.append(f"Low liquidity: ${total_liquidity:.2f} < ${min_liquidity:.2f}")
        
        if total_liquidity == 0:
            risk_score += 0.5
            reasons.append("No liquidity found")
        
        # Проверка блокировки LP
        if not features.get("lp_locked", False):
            risk_score += 0.2
            reasons.append("LP tokens not locked")
        else:
            lp_lock_percent = features.get("lp_lock_percent", 0.0) or 0.0
            if lp_lock_percent < 80.0:
                risk_score += 0.1
                reasons.append(f"Low LP lock percentage: {lp_lock_percent}%")
        
        # Проверка торговой активности
        volume_24h = features.get("volume_24h_usd", 0.0) or 0.0
        if volume_24h == 0:
            risk_score += 0.1
            reasons.append("No trading volume in last 24h")
        
        buy_sell_ratio = features.get("buy_sell_ratio", 0.0) or 0.0
        if buy_sell_ratio > 10.0:  # Много покупателей, мало продавцов
            risk_score += 0.15
            reasons.append("Suspicious buy/sell ratio (possible pump)")
        
        # Нормализация скора
        scam_score = min(1.0, risk_score)
        
        # Определение класса
        if scam_score >= self.high_risk_threshold:
            scam_class = "scam" if scam_score >= 0.8 else "high_risk"
        elif scam_score >= self.medium_risk_threshold:
            scam_class = "medium_risk"
        elif scam_score > 0.2:
            scam_class = "low_risk"
        else:
            scam_class = "safe"
        
        result = {
            "scam_score": scam_score,
            "scam_class": scam_class,
            "reasons": reasons,
        }
        
        logger.info(
            "Rule-based detection completed",
            scam_score=scam_score,
            scam_class=scam_class,
            reasons_count=len(reasons)
        )
        
        return result

