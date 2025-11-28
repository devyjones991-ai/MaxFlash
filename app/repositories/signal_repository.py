"""
Репозиторий для работы с сигналами.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime
from app.models.signal import Signal, SignalRating, SignalType


class SignalRepository:
    """Репозиторий для сигналов."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, signal_data: dict) -> Signal:
        """Создать новый сигнал."""
        signal = Signal(**signal_data)
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        return signal
    
    async def get_active_signals(
        self,
        rating: Optional[SignalRating] = None,
        limit: int = 100
    ) -> List[Signal]:
        """Получить активные сигналы."""
        query = select(Signal).where(Signal.is_active == True)
        
        if rating:
            query = query.where(Signal.rating == rating)
        
        query = query.order_by(Signal.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_id(self, signal_id: int) -> Optional[Signal]:
        """Получить сигнал по ID."""
        result = await self.db.execute(
            select(Signal).where(Signal.id == signal_id)
        )
        return result.scalar_one_or_none()
    
    async def mark_as_sent(self, signal_id: int):
        """Отметить сигнал как отправленный."""
        signal = await self.get_by_id(signal_id)
        if signal:
            signal.is_sent = True
            signal.sent_at = datetime.utcnow()
            await self.db.commit()

