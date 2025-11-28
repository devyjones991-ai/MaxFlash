"""
Менеджер ордеров для управления стоп-лоссами, тейк-профитами и трейлинг-стопами.
"""
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from api.exchange_adapter import ExchangeAdapter

logger = logging.getLogger(__name__)


@dataclass
class OrderInfo:
    """Информация об ордере."""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', 'stop', 'stop_limit'
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str = 'pending'  # 'pending', 'open', 'closed', 'cancelled'
    created_at: datetime = None
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_amount: float = 0.0

    def __post_init__(self):
        """Инициализация после создания."""
        if self.created_at is None:
            self.created_at = datetime.now()


class OrderManager:
    """
    Менеджер ордеров для управления стоп-лоссами, тейк-профитами и др.
    """

    def __init__(self, exchange_adapter: ExchangeAdapter):
        """
        Инициализация менеджера ордеров.

        Args:
            exchange_adapter: Адаптер биржи
        """
        self.exchange_adapter = exchange_adapter
        self.orders: Dict[str, OrderInfo] = {}  # order_id -> OrderInfo
        self.monitoring_task: Optional[asyncio.Task] = None

    def add_order(self, order_data: Dict) -> OrderInfo:
        """
        Добавить ордер в отслеживание.

        Args:
            order_data: Данные ордера от биржи

        Returns:
            OrderInfo объект
        """
        order_info = OrderInfo(
            order_id=order_data.get('id', ''),
            symbol=order_data.get('symbol', ''),
            side=order_data.get('side', ''),
            order_type=order_data.get('type', ''),
            amount=order_data.get('amount', 0),
            price=order_data.get('price'),
            stop_price=order_data.get('stopPrice'),
            status=order_data.get('status', 'pending')
        )

        self.orders[order_info.order_id] = order_info
        logger.info(
            "Добавлен ордер в отслеживание: %s %s %s",
            order_info.symbol, order_info.side, order_info.order_id
        )

        return order_info

    async def create_stop_loss(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float
    ) -> Optional[OrderInfo]:
        """
        Создать стоп-лосс ордер.

        Args:
            symbol: Торговая пара
            side: 'buy' или 'sell'
            amount: Количество
            stop_price: Цена срабатывания

        Returns:
            OrderInfo или None при ошибке
        """
        try:
            order = await self.exchange_adapter.create_stop_loss_order(
                symbol=symbol,
                side=side,
                amount=amount,
                stop_price=stop_price
            )

            order_info = self.add_order(order)
            logger.info(
                "Создан стоп-лосс ордер: %s @ %.2f",
                symbol, stop_price
            )

            return order_info

        except Exception as e:
            logger.error(
                "Ошибка создания стоп-лосс ордера: %s", str(e), exc_info=True
            )
            return None

    async def create_take_profit(
        self,
        symbol: str,
        side: str,
        amount: float,
        take_profit_price: float
    ) -> Optional[OrderInfo]:
        """
        Создать тейк-профит ордер (лимитный).

        Args:
            symbol: Торговая пара
            side: 'buy' или 'sell'
            amount: Количество
            take_profit_price: Цена тейк-профита

        Returns:
            OrderInfo или None при ошибке
        """
        try:
            order = await self.exchange_adapter.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=take_profit_price
            )

            order_info = self.add_order(order)
            logger.info(
                "Создан тейк-профит ордер: %s @ %.2f",
                symbol, take_profit_price
            )

            return order_info

        except Exception as e:
            logger.error(
                "Ошибка создания тейк-профит ордера: %s",
                str(e), exc_info=True
            )
            return None

    async def update_stop_loss(
        self,
        order_id: str,
        new_stop_price: float
    ) -> bool:
        """
        Обновить стоп-лосс ордер.

        Args:
            order_id: ID существующего стоп-лосс ордера
            new_stop_price: Новая цена стоп-лосса

        Returns:
            True если успешно
        """
        if order_id not in self.orders:
            logger.warning("Ордер %s не найден", order_id)
            return False

        order_info = self.orders[order_id]

        try:
            # Отменяем старый ордер
            await self.exchange_adapter.cancel_order(
                order_id, order_info.symbol
            )

            # Создаем новый стоп-лосс
            new_order = await self.exchange_adapter.create_stop_loss_order(
                symbol=order_info.symbol,
                side=order_info.side,
                amount=order_info.amount,
                stop_price=new_stop_price
            )

            # Обновляем информацию
            order_info.status = 'cancelled'
            new_order_info = self.add_order(new_order)
            new_order_info.stop_price = new_stop_price

            logger.info(
                "Обновлен стоп-лосс: %s -> %.2f",
                order_id, new_stop_price
            )

            return True

        except Exception as e:
            logger.error(
                "Ошибка обновления стоп-лосса %s: %s",
                order_id, str(e), exc_info=True
            )
            return False

    async def cancel_order(self, order_id: str) -> bool:
        """
        Отменить ордер.

        Args:
            order_id: ID ордера

        Returns:
            True если успешно
        """
        if order_id not in self.orders:
            logger.warning("Ордер %s не найден", order_id)
            return False

        order_info = self.orders[order_id]

        try:
            await self.exchange_adapter.cancel_order(
                order_id, order_info.symbol
            )

            order_info.status = 'cancelled'
            logger.info("Ордер отменен: %s", order_id)

            return True

        except Exception as e:
            logger.error(
                "Ошибка отмены ордера %s: %s",
                order_id, str(e), exc_info=True
            )
            return False

    async def monitor_orders(self, interval: int = 10):
        """
        Мониторинг статусов ордеров.

        Args:
            interval: Интервал проверки в секундах
        """
        while True:
            try:
                await self.update_order_statuses()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("Мониторинг ордеров остановлен")
                break
            except Exception as e:
                logger.error(
                    "Ошибка мониторинга ордеров: %s", str(e), exc_info=True
                )
                await asyncio.sleep(interval)

    async def update_order_statuses(self):
        """Обновить статусы всех отслеживаемых ордеров."""
        for order_id, order_info in list(self.orders.items()):
            if order_info.status in ['closed', 'cancelled']:
                continue

            try:
                order = await self.exchange_adapter.async_exchange.fetch_order(
                    order_id, order_info.symbol
                )

                # Обновляем статус
                order_info.status = order.get('status', order_info.status)

                # Обновляем данные о заполнении
                if order_info.status == 'closed':
                    order_info.filled_at = datetime.now()
                    order_info.filled_price = order.get('average', order_info.price)
                    order_info.filled_amount = order.get('filled', 0)

                    logger.info(
                        "Ордер исполнен: %s @ %.2f",
                        order_id, order_info.filled_price
                    )

            except Exception as e:
                logger.debug(
                    "Ошибка обновления статуса ордера %s: %s",
                    order_id, str(e)
                )

    def get_order(self, order_id: str) -> Optional[OrderInfo]:
        """Получить информацию об ордере."""
        return self.orders.get(order_id)

    def get_orders_by_symbol(
        self,
        symbol: str,
        status: Optional[str] = None
    ) -> List[OrderInfo]:
        """
        Получить ордера по символу.

        Args:
            symbol: Торговая пара
            status: Фильтр по статусу (опционально)

        Returns:
            Список ордеров
        """
        orders = [
            o for o in self.orders.values()
            if o.symbol == symbol
        ]

        if status:
            orders = [o for o in orders if o.status == status]

        return orders

    def start_monitoring(self, interval: int = 10):
        """Запустить мониторинг ордеров."""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(
                self.monitor_orders(interval)
            )
            logger.info("Мониторинг ордеров запущен")

    def stop_monitoring(self):
        """Остановить мониторинг ордеров."""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            logger.info("Мониторинг ордеров остановлен")

