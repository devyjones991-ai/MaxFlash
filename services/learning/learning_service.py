"""
Сервис самообучения для торговых стратегий.
"""
from typing import Dict, Optional
import structlog
from datetime import datetime
from app.database import AsyncSession
from app.models.trade import Trade, TradeStatus
from services.learning.bandit_learner import ContextualBandit
from sqlalchemy import select

logger = structlog.get_logger()


class LearningService:
    """Сервис самообучения."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Инициализация контекстного бандита
        context_features = ["volatility", "trend", "volume", "liquidity"]
        self.bandit = ContextualBandit(context_features)
        
        # Дефолтные руки (варианты параметров)
        default_arms = [
            {"position_size": 0.01, "stop_loss": 0.02, "take_profit": 0.05},
            {"position_size": 0.02, "stop_loss": 0.03, "take_profit": 0.06},
            {"position_size": 0.015, "stop_loss": 0.025, "take_profit": 0.055},
            {"position_size": 0.025, "stop_loss": 0.04, "take_profit": 0.08},
        ]
        
        # Инициализируем бандиты для разных контекстов
        for context_key in ["low_vol", "medium_vol", "high_vol"]:
            self.bandit.initialize_bandit(context_key, default_arms)
    
    def calculate_reward(self, trade: Trade) -> float:
        """
        Рассчитать награду для сделки.
        
        Args:
            trade: Модель сделки
        
        Returns:
            Награда в диапазоне [0.0, 1.0]
        """
        if not trade.pnl_percent:
            return 0.0
        
        pnl_percent = float(trade.pnl_percent)
        
        # Нормализуем PnL в [0, 1]
        # Предполагаем, что хорошая сделка = +10%, плохая = -10%
        if pnl_percent >= 10.0:
            reward = 1.0
        elif pnl_percent <= -10.0:
            reward = 0.0
        else:
            # Линейная нормализация
            reward = (pnl_percent + 10.0) / 20.0
        
        return max(0.0, min(1.0, reward))
    
    def extract_context(self, signal_data: Dict) -> Dict:
        """
        Извлечь контекст из данных сигнала.
        
        Args:
            signal_data: Данные сигнала
        
        Returns:
            Словарь с фичами контекста
        """
        # Упрощённая версия - в реальности нужно извлекать из данных
        return {
            "volatility": signal_data.get("volatility", 0.2),
            "trend": signal_data.get("trend", 0.0),
            "volume": signal_data.get("volume", 0.0),
            "liquidity": signal_data.get("liquidity", 0.0),
        }
    
    async def get_trading_params(
        self,
        signal_data: Dict
    ) -> Dict:
        """
        Получить параметры торговли на основе обучения.
        
        Args:
            signal_data: Данные сигнала
        
        Returns:
            Словарь с параметрами: position_size, stop_loss, take_profit
        """
        context = self.extract_context(signal_data)
        context_key, arm_index, arm_params = self.bandit.select_arm(context)
        
        logger.info(
            "Trading params selected",
            context_key=context_key,
            arm_index=arm_index,
            params=arm_params
        )
        
        return arm_params
    
    async def learn_from_trade(self, trade: Trade):
        """
        Обучиться на основе завершённой сделки.
        
        Args:
            trade: Завершённая сделка
        """
        if trade.status != TradeStatus.CLOSED:
            return
        
        # Получаем сигнал для извлечения контекста
        if trade.signal_id:
            from app.repositories.signal_repository import SignalRepository
            signal_repo = SignalRepository(self.db)
            signal = await signal_repo.get_by_id(trade.signal_id)
            
            if signal:
                signal_data = {
                    "volatility": 0.2,  # TODO: извлечь из данных
                    "trend": 0.0,
                    "volume": 0.0,
                    "liquidity": 0.0,
                }
                context = self.extract_context(signal_data)
                
                # Рассчитываем награду
                reward = self.calculate_reward(trade)
                
                # Определяем индекс руки из параметров сделки
                # Упрощённо - находим ближайшую руку
                arm_index = 0  # TODO: найти правильный индекс
                
                # Обновляем бандит
                self.bandit.update(context, arm_index, reward)
                
                logger.info(
                    "Learned from trade",
                    trade_id=trade.id,
                    reward=reward,
                    pnl_percent=trade.pnl_percent
                )
    
    async def learn_from_closed_trades(self, limit: int = 100):
        """
        Обучиться на основе последних закрытых сделок.
        
        Args:
            limit: Максимальное количество сделок для обучения
        """
        result = await self.db.execute(
            select(Trade).where(
                Trade.status == TradeStatus.CLOSED
            ).order_by(Trade.closed_at.desc()).limit(limit)
        )
        trades = result.scalars().all()
        
        for trade in trades:
            await self.learn_from_trade(trade)
        
        logger.info("Batch learning completed", trades_count=len(trades))
    
    def get_learning_statistics(self) -> Dict:
        """Получить статистику обучения."""
        return self.bandit.get_statistics()

