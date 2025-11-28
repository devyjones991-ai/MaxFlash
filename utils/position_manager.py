"""
Менеджер позиций для отслеживания и управления открытыми позициями.
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PositionStatus(str, Enum):
    """Статусы позиции."""
    OPEN = "open"
    PARTIALLY_CLOSED = "partially_closed"
    CLOSED = "closed"
    STOPPED_OUT = "stopped_out"


@dataclass
class Position:
    """Данные позиции."""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    current_price: float
    size: float  # Размер позиции в базовой валюте
    stop_loss: float
    take_profit: float
    status: PositionStatus = PositionStatus.OPEN
    pnl: float = 0.0
    pnl_percent: float = 0.0
    opened_at: datetime = None
    closed_at: Optional[datetime] = None
    order_id: Optional[str] = None
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None

    def __post_init__(self):
        """Инициализация после создания."""
        if self.opened_at is None:
            self.opened_at = datetime.now()


class PositionManager:
    """
    Менеджер позиций для отслеживания открытых позиций.
    """

    def __init__(self):
        """Инициализация менеджера позиций."""
        self.positions: Dict[str, Position] = {}  # symbol -> Position

    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        size: float,
        stop_loss: float,
        take_profit: float,
        order_id: Optional[str] = None
    ) -> Position:
        """
        Добавить новую позицию.

        Args:
            symbol: Торговая пара
            side: 'long' или 'short'
            entry_price: Цена входа
            size: Размер позиции
            stop_loss: Цена стоп-лосса
            take_profit: Цена тейк-профита
            order_id: ID ордера

        Returns:
            Созданная позиция
        """
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            current_price=entry_price,
            size=size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_id=order_id
        )

        self.positions[symbol] = position
        logger.info(
            "Добавлена позиция: %s %s @ %.2f, размер=%.2f",
            symbol, side, entry_price, size
        )

        return position

    def update_price(self, symbol: str, current_price: float):
        """
        Обновить текущую цену позиции.

        Args:
            symbol: Торговая пара
            current_price: Текущая цена
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        position.current_price = current_price

        # Рассчитываем P&L
        if position.side == 'long':
            position.pnl = (
                (current_price - position.entry_price) * position.size
            )
            position.pnl_percent = (
                ((current_price - position.entry_price) /
                 position.entry_price) * 100
            )
        else:  # short
            position.pnl = (
                (position.entry_price - current_price) * position.size
            )
            position.pnl_percent = (
                ((position.entry_price - current_price) /
                 position.entry_price) * 100
            )

    def update_stop_loss(
        self,
        symbol: str,
        new_stop_loss: float
    ):
        """
        Обновить стоп-лосс позиции.

        Args:
            symbol: Торговая пара
            new_stop_loss: Новая цена стоп-лосса
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        old_stop_loss = position.stop_loss

        # Проверяем, что новый стоп лучше старого
        if position.side == 'long':
            if new_stop_loss > old_stop_loss:
                position.stop_loss = new_stop_loss
                logger.info(
                    "Обновлен стоп-лосс для %s: %.2f -> %.2f",
                    symbol, old_stop_loss, new_stop_loss
                )
        else:  # short
            if new_stop_loss < old_stop_loss:
                position.stop_loss = new_stop_loss
                logger.info(
                    "Обновлен стоп-лосс для %s: %.2f -> %.2f",
                    symbol, old_stop_loss, new_stop_loss
                )

    def close_position(
        self,
        symbol: str,
        close_price: Optional[float] = None,
        reason: str = "manual"
    ):
        """
        Закрыть позицию.

        Args:
            symbol: Торговая пара
            close_price: Цена закрытия (если None, используется текущая)
            reason: Причина закрытия
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        if close_price is None:
            close_price = position.current_price

        # Обновляем цену и P&L
        self.update_price(symbol, close_price)

        # Обновляем статус
        if reason == "stop_loss":
            position.status = PositionStatus.STOPPED_OUT
        else:
            position.status = PositionStatus.CLOSED

        position.closed_at = datetime.now()

        logger.info(
            "Позиция закрыта: %s @ %.2f, P&L=%.2f (%.2f%%), причина=%s",
            symbol, close_price, position.pnl, position.pnl_percent, reason
        )

    def partial_close(
        self,
        symbol: str,
        close_percent: float,
        close_price: Optional[float] = None
    ):
        """
        Частично закрыть позицию.

        Args:
            symbol: Торговая пара
            close_percent: Процент для закрытия
            close_price: Цена закрытия
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        if close_price is None:
            close_price = position.current_price

        # Уменьшаем размер позиции
        close_size = position.size * (close_percent / 100.0)
        position.size -= close_size

        if position.size <= 0:
            self.close_position(symbol, close_price, "partial_close")
        else:
            position.status = PositionStatus.PARTIALLY_CLOSED
            logger.info(
                "Частично закрыта позиция %s: %.2f%% @ %.2f",
                symbol, close_percent, close_price
            )

    def get_position(self, symbol: str) -> Optional[Position]:
        """Получить позицию по символу."""
        return self.positions.get(symbol)

    def get_all_positions(
        self,
        status: Optional[PositionStatus] = None
    ) -> List[Position]:
        """
        Получить все позиции.

        Args:
            status: Фильтр по статусу (если None, возвращаются все)

        Returns:
            Список позиций
        """
        if status is None:
            return list(self.positions.values())

        return [
            pos for pos in self.positions.values()
            if pos.status == status
        ]

    def get_open_positions(self) -> List[Position]:
        """Получить все открытые позиции."""
        return self.get_all_positions(PositionStatus.OPEN)

    def get_total_pnl(self) -> float:
        """Получить общий P&L по всем позициям."""
        return sum(pos.pnl for pos in self.positions.values())

    def get_statistics(self) -> Dict:
        """Получить статистику по позициям."""
        open_positions = self.get_open_positions()
        closed_positions = self.get_all_positions(PositionStatus.CLOSED)
        stopped_positions = self.get_all_positions(
            PositionStatus.STOPPED_OUT
        )

        total_pnl = self.get_total_pnl()
        winning_positions = [
            p for p in closed_positions if p.pnl > 0
        ]
        losing_positions = [
            p for p in closed_positions + stopped_positions if p.pnl < 0
        ]

        return {
            'total_positions': len(self.positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'stopped_positions': len(stopped_positions),
            'winning_positions': len(winning_positions),
            'losing_positions': len(losing_positions),
            'total_pnl': total_pnl,
            'avg_win': (
                sum(p.pnl for p in winning_positions) / len(winning_positions)
                if winning_positions else 0.0
            ),
            'avg_loss': (
                sum(p.pnl for p in losing_positions) / len(losing_positions)
                if losing_positions else 0.0
            ),
            'win_rate': (
                len(winning_positions) /
                (len(winning_positions) + len(losing_positions)) * 100
                if (winning_positions or losing_positions) else 0.0
            )
        }

