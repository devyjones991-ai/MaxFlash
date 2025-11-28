"""
Риск-менеджмент для торговли.
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import structlog
from app.config import settings
from app.database import AsyncSession
from sqlalchemy import select, func
from app.models.trade import Trade, TradeStatus

logger = structlog.get_logger()


class RiskManager:
    """Менеджер рисков."""
    
    def __init__(self, db: AsyncSession, binance_client):
        self.db = db
        self.binance_client = binance_client
        self.max_position_size_usd = settings.MAX_POSITION_SIZE_USD
        self.max_daily_loss_usd = settings.MAX_DAILY_LOSS_USD
        self.max_slippage_percent = settings.MAX_SLIPPAGE_PERCENT
    
    async def check_daily_loss_limit(self) -> bool:
        """
        Проверить, не превышен ли дневной лимит убытков.
        
        Returns:
            True если можно торговать, False если лимит превышен
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Получаем все закрытые сделки за сегодня
        result = await self.db.execute(
            select(Trade).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.closed_at >= today_start
            )
        )
        trades = result.scalars().all()
        
        total_loss = sum(
            float(t.pnl or 0) for t in trades
            if t.pnl and float(t.pnl) < 0
        )
        
        if abs(total_loss) >= self.max_daily_loss_usd:
            logger.warning(
                "Daily loss limit exceeded",
                total_loss=total_loss,
                limit=self.max_daily_loss_usd
            )
            return False
        
        return True
    
    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        risk_percent: float = 2.0  # 2% от капитала
    ) -> float:
        """
        Рассчитать размер позиции на основе риска.
        
        Args:
            symbol: Торговая пара
            entry_price: Цена входа
            risk_percent: Процент риска от капитала
        
        Returns:
            Размер позиции в базовой валюте
        """
        # Получаем баланс
        balance = self.binance_client.get_balance("USDT")
        
        if balance <= 0:
            return 0.0
        
        # Рассчитываем размер позиции
        risk_amount = balance * (risk_percent / 100.0)
        
        # Ограничиваем максимальным размером позиции
        position_size_usd = min(risk_amount, self.max_position_size_usd)
        
        # Конвертируем в количество базовой валюты
        # Упрощённо, в реальности нужно учитывать точность символа
        quantity = position_size_usd / entry_price
        
        logger.info(
            "Position size calculated",
            symbol=symbol,
            balance=balance,
            position_size_usd=position_size_usd,
            quantity=quantity
        )
        
        return quantity
    
    def validate_slippage(
        self,
        expected_price: float,
        actual_price: float
    ) -> bool:
        """
        Проверить, не превышен ли slippage.
        
        Args:
            expected_price: Ожидаемая цена
            actual_price: Фактическая цена
        
        Returns:
            True если slippage в пределах нормы
        """
        if expected_price == 0:
            return False
        
        slippage_percent = abs((actual_price - expected_price) / expected_price) * 100
        
        if slippage_percent > self.max_slippage_percent:
            logger.warning(
                "Slippage exceeded",
                expected=expected_price,
                actual=actual_price,
                slippage_percent=slippage_percent
            )
            return False
        
        return True
    
    async def check_max_open_positions(self, max_positions: int = 5) -> bool:
        """
        Проверить, не превышено ли максимальное количество открытых позиций.
        
        Args:
            max_positions: Максимальное количество позиций
        
        Returns:
            True если можно открыть новую позицию
        """
        result = await self.db.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.OPEN
            )
        )
        open_count = result.scalar() or 0
        
        if open_count >= max_positions:
            logger.warning(
                "Max open positions reached",
                open_count=open_count,
                max=max_positions
            )
            return False
        
        return True
    
    async def validate_trade(
        self,
        symbol: str,
        entry_price: float,
        quantity: float
    ) -> Dict[str, bool]:
        """
        Валидировать сделку перед исполнением.
        
        Returns:
            Словарь с результатами валидации
        """
        results = {
            "daily_loss_ok": await self.check_daily_loss_limit(),
            "max_positions_ok": await self.check_max_open_positions(),
            "position_size_ok": True,
        }
        
        # Проверка размера позиции
        position_size_usd = quantity * entry_price
        if position_size_usd > self.max_position_size_usd:
            results["position_size_ok"] = False
        
        results["valid"] = all(results.values())
        
        return results

