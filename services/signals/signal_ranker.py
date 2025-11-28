"""
Ранжирование сигналов по качеству.
"""
from typing import List
from app.models.signal import Signal, SignalRating
import structlog

logger = structlog.get_logger()


class SignalRanker:
    """Ранжирование сигналов."""
    
    def rank_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        Отсортировать сигналы по качеству.
        
        Args:
            signals: Список сигналов
        
        Returns:
            Отсортированный список сигналов
        """
        # Сортируем по комбинации score и rating
        def sort_key(signal: Signal) -> tuple:
            # Приоритет по rating
            rating_priority = {
                SignalRating.ALPHA: 3,
                SignalRating.PRO: 2,
                SignalRating.FREE: 1,
            }
            
            # Комбинированный score
            rating_score = rating_priority.get(signal.rating, 0)
            signal_score = float(signal.signal_score or 0.0)
            
            return (rating_score, signal_score)
        
        sorted_signals = sorted(signals, key=sort_key, reverse=True)
        
        logger.info("Signals ranked", count=len(sorted_signals))
        
        return sorted_signals
    
    def filter_by_rating(
        self,
        signals: List[Signal],
        rating: SignalRating
    ) -> List[Signal]:
        """
        Отфильтровать сигналы по рейтингу.
        
        Args:
            signals: Список сигналов
            rating: Рейтинг для фильтрации
        """
        filtered = [s for s in signals if s.rating == rating]
        return filtered
    
    def get_top_signals(
        self,
        signals: List[Signal],
        limit: int = 10,
        rating: SignalRating = None
    ) -> List[Signal]:
        """
        Получить топ сигналов.
        
        Args:
            signals: Список сигналов
            limit: Максимальное количество
            rating: Опциональный фильтр по рейтингу
        """
        ranked = self.rank_signals(signals)
        
        if rating:
            ranked = self.filter_by_rating(ranked, rating)
        
        return ranked[:limit]

