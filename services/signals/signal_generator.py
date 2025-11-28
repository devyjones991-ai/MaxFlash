"""
Генератор торговых сигналов.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import structlog
from app.database import AsyncSession
from app.models.signal import Signal, SignalRating, SignalType
from app.models.token import Token
from app.repositories.token_repository import TokenRepository
from app.repositories.signal_repository import SignalRepository
from app.config import settings

logger = structlog.get_logger()


class SignalGenerator:
    """Генератор торговых сигналов."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_repo = TokenRepository(db)
        self.signal_repo = SignalRepository(db)
    
    def calculate_signal_score(
        self,
        token: Token,
        pools: List
    ) -> float:
        """
        Рассчитать score сигнала (0.0 - 1.0).
        
        Args:
            token: Модель токена
            pools: Список пулов токена
        """
        score = 0.0
        
        # Базовый score от scam score (инвертированный)
        scam_score = float(token.scam_score or 0.0)
        safety_score = 1.0 - scam_score
        score += safety_score * 0.4  # 40% веса на безопасность
        
        # Score от ликвидности
        if pools:
            total_liquidity = sum(float(p.liquidity_usd or 0) for p in pools)
            min_liquidity = settings.MIN_LIQUIDITY_USD
            
            if total_liquidity >= min_liquidity * 10:
                liquidity_score = 1.0
            elif total_liquidity >= min_liquidity:
                liquidity_score = (total_liquidity / (min_liquidity * 10))
            else:
                liquidity_score = 0.0
            
            score += liquidity_score * 0.3  # 30% веса на ликвидность
        
        # Score от торговой активности
        if pools:
            total_volume = sum(float(p.volume_24h_usd or 0) for p in pools)
            if total_volume > 100000:  # $100k+
                volume_score = min(1.0, total_volume / 1000000)  # Нормализуем до $1M
            else:
                volume_score = total_volume / 100000
            
            score += volume_score * 0.2  # 20% веса на объём
        
        # Score от блокировки LP
        if pools:
            lp_locked_count = sum(1 for p in pools if p.lp_locked)
            if lp_locked_count > 0:
                lp_score = lp_locked_count / len(pools)
                score += lp_score * 0.1  # 10% веса на блокировку LP
        
        return min(1.0, score)
    
    def determine_signal_rating(self, signal_score: float) -> SignalRating:
        """
        Определить рейтинг сигнала на основе score.
        
        Args:
            signal_score: Score сигнала (0.0 - 1.0)
        """
        if signal_score >= settings.SIGNAL_ALPHA_MIN_SCORE:
            return SignalRating.ALPHA
        elif signal_score >= settings.SIGNAL_PRO_MIN_SCORE:
            return SignalRating.PRO
        else:
            return SignalRating.FREE
    
    def generate_signal_description(
        self,
        token: Token,
        signal_type: SignalType,
        signal_score: float
    ) -> Dict[str, str]:
        """
        Сгенерировать описание сигнала.
        
        Returns:
            Словарь с title, description, full_description
        """
        scam_class = token.scam_class or "unknown"
        rating = self.determine_signal_rating(signal_score)
        
        title = f"{token.symbol} {signal_type.value.upper()} Signal ({rating.value.upper()})"
        
        description = (
            f"Trading signal for {token.symbol}.\n"
            f"Risk level: {scam_class}\n"
            f"Signal score: {signal_score:.2%}\n"
            f"Rating: {rating.value}"
        )
        
        full_description = (
            f"# {title}\n\n"
            f"## Token Information\n"
            f"- Symbol: {token.symbol}\n"
            f"- Address: {token.address}\n"
            f"- Chain: {token.chain}\n"
            f"- Scam Score: {float(token.scam_score or 0):.2%}\n"
            f"- Risk Class: {scam_class}\n\n"
            f"## Signal Details\n"
            f"- Type: {signal_type.value.upper()}\n"
            f"- Score: {signal_score:.2%}\n"
            f"- Rating: {rating.value}\n"
            f"- Confidence: High\n\n"
            f"## Risk Factors\n"
        )
        
        if token.scam_reasons:
            for reason in token.scam_reasons:
                full_description += f"- {reason}\n"
        
        return {
            "title": title,
            "description": description,
            "full_description": full_description,
        }
    
    async def generate_signals_for_token(
        self,
        token_id: int,
        signal_type: SignalType = SignalType.LONG
    ) -> Optional[Signal]:
        """
        Сгенерировать сигнал для токена.
        
        Args:
            token_id: ID токена
            signal_type: Тип сигнала
        """
        # Получаем токен
        # В реальности нужно использовать репозиторий, но для упрощения используем прямой запрос
        from sqlalchemy import select
        result = await self.db.execute(
            select(Token).where(Token.id == token_id)
        )
        token = result.scalar_one_or_none()
        
        if not token:
            logger.warning("Token not found", token_id=token_id)
            return None
        
        # Проверяем, что токен не скам
        scam_score = float(token.scam_score or 0.0)
        if scam_score >= settings.SCAM_SCORE_THRESHOLD_HIGH:
            logger.info("Token is scam, skipping signal generation", token_id=token_id)
            return None
        
        # Получаем пулы
        pools = await self.token_repo.get_pools_by_token(token_id)
        
        if not pools:
            logger.warning("No pools found for token", token_id=token_id)
            return None
        
        # Рассчитываем score
        signal_score = self.calculate_signal_score(token, pools)
        
        # Определяем рейтинг
        rating = self.determine_signal_rating(signal_score)
        
        # Генерируем описание
        descriptions = self.generate_signal_description(token, signal_type, signal_score)
        
        # Получаем текущую цену (упрощённо, в реальности из пула или API)
        current_price = 0.0  # TODO: получить реальную цену
        
        # Рассчитываем entry, SL, TP (упрощённо)
        entry_price = current_price
        stop_loss = entry_price * 0.95 if signal_type == SignalType.LONG else entry_price * 1.05
        take_profit = entry_price * 1.10 if signal_type == SignalType.LONG else entry_price * 0.90
        
        # Создаём сигнал
        signal_data = {
            "token_id": token_id,
            "symbol": token.symbol,
            "signal_type": signal_type,
            "rating": rating,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "current_price": current_price,
            "signal_score": signal_score,
            "confidence": signal_score,  # Упрощённо
            "risk_score": scam_score,
            "title": descriptions["title"],
            "description": descriptions["description"],
            "full_description": descriptions["full_description"],
            "timeframe": "15m",
            "is_active": True,
            "expires_at": datetime.utcnow() + timedelta(hours=24),
        }
        
        signal = await self.signal_repo.create(signal_data)
        
        logger.info(
            "Signal generated",
            signal_id=signal.id,
            symbol=token.symbol,
            rating=rating.value,
            score=signal_score
        )
        
        return signal
    
    async def generate_signals_batch(
        self,
        token_ids: List[int],
        signal_type: SignalType = SignalType.LONG
    ) -> List[Signal]:
        """
        Сгенерировать сигналы для списка токенов.
        
        Args:
            token_ids: Список ID токенов
            signal_type: Тип сигнала
        """
        signals = []
        
        for token_id in token_ids:
            try:
                signal = await self.generate_signals_for_token(token_id, signal_type)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(
                    "Error generating signal",
                    token_id=token_id,
                    error=str(e)
                )
                continue
        
        logger.info("Batch signal generation completed", signals_count=len(signals))
        return signals

