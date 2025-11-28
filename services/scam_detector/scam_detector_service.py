"""
Сервис детекции скама токенов.
"""
from typing import Dict, Optional
import structlog
from app.database import AsyncSession
from app.repositories.token_repository import TokenRepository
from services.scam_detector.feature_extractor import ScamFeatureExtractor
from services.scam_detector.rule_based_detector import RuleBasedScamDetector
from app.config import settings

logger = structlog.get_logger()


class ScamDetectorService:
    """Сервис детекции скама."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_repo = TokenRepository(db)
        
        # Инициализация детекторов
        self.eth_extractor = ScamFeatureExtractor(
            settings.ETH_RPC_URL,
            "ethereum"
        )
        self.bsc_extractor = ScamFeatureExtractor(
            settings.BSC_RPC_URL,
            "bsc"
        )
        self.rule_detector = RuleBasedScamDetector()
    
    async def analyze_token(
        self,
        token_address: str,
        chain: str
    ) -> Dict:
        """
        Проанализировать токен на скам.
        
        Args:
            token_address: Адрес токена
            chain: 'ethereum' или 'bsc'
        
        Returns:
            Словарь с результатами анализа
        """
        logger.info("Analyzing token for scam", token=token_address, chain=chain)
        
        # Выбираем экстрактор фич
        extractor = self.eth_extractor if chain == "ethereum" else self.bsc_extractor
        
        # Получаем токен из БД
        token = await self.token_repo.get_by_address(token_address, chain)
        
        if not token:
            logger.warning("Token not found in DB", token=token_address)
            return {
                "error": "Token not found in database",
                "scam_score": 1.0,
                "scam_class": "unknown"
            }
        
        # Получаем пулы токена
        pools = await self.token_repo.get_pools_by_token(token.id)
        pools_data = [
            {
                "pool_address": p.pool_address,
                "liquidity_usd": float(p.liquidity_usd or 0),
                "lp_locked": p.lp_locked,
                "lp_lock_percent": float(p.lp_lock_percent or 0),
                "volume_24h_usd": float(p.volume_24h_usd or 0),
                "transactions_24h": p.transactions_24h or 0,
                "unique_buyers_24h": p.unique_buyers_24h or 0,
                "unique_sellers_24h": p.unique_sellers_24h or 0,
            }
            for p in pools
        ]
        
        # Извлекаем фичи
        features = await extractor.extract_all_features(token_address, pools_data)
        
        # Добавляем фичи из БД
        features.update({
            "is_proxy": token.is_proxy,
            "is_upgradeable": token.is_upgradeable,
            "has_blacklist": token.has_blacklist,
            "has_whitelist": token.has_whitelist,
            "has_mint": token.has_mint,
            "has_pause": token.has_pause,
            "tax_buy_percent": float(token.tax_buy_percent or 0),
            "tax_sell_percent": float(token.tax_sell_percent or 0),
        })
        
        # Rule-based детекция
        detection_result = self.rule_detector.detect(features)
        
        # Обновляем токен в БД
        await self.token_repo.update(token, {
            "scam_score": detection_result["scam_score"],
            "scam_class": detection_result["scam_class"],
            "scam_reasons": detection_result["reasons"],
            **{k: v for k, v in features.items() if k in [
                "is_proxy", "is_upgradeable", "has_blacklist",
                "has_whitelist", "has_mint", "has_pause",
                "tax_buy_percent", "tax_sell_percent"
            ]}
        })
        
        logger.info(
            "Token analysis completed",
            token=token_address,
            scam_score=detection_result["scam_score"],
            scam_class=detection_result["scam_class"]
        )
        
        return {
            "token_address": token_address,
            "chain": chain,
            "scam_score": detection_result["scam_score"],
            "scam_class": detection_result["scam_class"],
            "reasons": detection_result["reasons"],
            "features": features,
        }

