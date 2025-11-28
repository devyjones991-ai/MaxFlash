"""
Исполнитель торговых операций с async поддержкой.
Интегрирует ExchangeAdapter и RiskManager для исполнения сделок.
"""
import logging
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime

from api.exchange_adapter import ExchangeAdapter, ExchangeType
from utils.risk_manager import RiskManager, RiskConfig

logger = logging.getLogger(__name__)


class TradingExecutor:
    """
    Исполнитель торговых операций.
    Управляет исполнением ордеров с учетом риск-менеджмента.
    """

    def __init__(
        self,
        exchange_adapter: ExchangeAdapter,
        risk_manager: RiskManager
    ):
        """
        Инициализация исполнителя.

        Args:
            exchange_adapter: Адаптер биржи
            risk_manager: Менеджер рисков
        """
        self.exchange_adapter = exchange_adapter
        self.risk_manager = risk_manager
        self.active_orders: Dict[str, Dict] = {}
        self.executed_trades: list = []

    async def execute_signal(
        self,
        symbol: str,
        signal_type: str,  # 'LONG' or 'SHORT'
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        account_balance: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Исполнить торговый сигнал.

        Args:
            symbol: Торговая пара
            signal_type: Тип сигнала ('LONG' или 'SHORT')
            entry_price: Цена входа
            stop_loss: Цена стоп-лосса
            take_profit: Цена тейк-профита
            account_balance: Баланс счета (если None, получаем с биржи)

        Returns:
            Информация о созданном ордере или None при ошибке
        """
        try:
            # Получаем баланс если не передан
            if account_balance is None:
                balance_data = await self.exchange_adapter.fetch_balance()
                account_balance = balance_data.get('USDT', {}).get('free', 0)
                if account_balance == 0:
                    # Пробуем получить общий баланс
                    account_balance = balance_data.get('total', {}).get('USDT', 0)

            if account_balance <= 0:
                logger.error("Недостаточно баланса для торговли")
                return None

            # Обновляем баланс в риск-менеджере
            self.risk_manager.set_balance(account_balance)

            # Рассчитываем размер позиции
            is_long = signal_type.upper() == 'LONG'
            position_size, risk_amount = (
                self.risk_manager.calculate_position_size(
                    entry_price=entry_price,
                    stop_loss_price=stop_loss,
                    account_balance=account_balance
                )
            )

            if position_size <= 0:
                logger.warning(
                    "Размер позиции равен 0 для %s", symbol
                )
                return None

            # Создаем основной ордер (лимитный для точного входа)
            side = 'buy' if is_long else 'sell'
            order = await self.exchange_adapter.create_limit_order(
                symbol=symbol,
                side=side,
                amount=position_size / entry_price,  # Конвертируем в количество
                price=entry_price
            )

            order_id = order.get('id')
            if not order_id:
                logger.error("Не удалось получить ID ордера")
                return None

            # Сохраняем информацию об ордере
            order_info = {
                'order_id': order_id,
                'symbol': symbol,
                'type': signal_type,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'risk_amount': risk_amount,
                'status': 'pending',
                'created_at': datetime.now(),
                'is_long': is_long
            }

            self.active_orders[order_id] = order_info

            logger.info(
                "Создан ордер для сигнала %s %s: размер=%.2f, риск=%.2f",
                symbol, signal_type, position_size, risk_amount
            )

            # Создаем стоп-лосс ордер (отложенный)
            try:
                stop_side = 'sell' if is_long else 'buy'
                stop_order = await (
                    self.exchange_adapter.create_stop_loss_order(
                        symbol=symbol,
                        side=stop_side,
                        amount=position_size / entry_price,
                        stop_price=stop_loss
                    )
                )
                order_info['stop_loss_order_id'] = stop_order.get('id')
            except Exception as e:
                logger.warning(
                    "Не удалось создать стоп-лосс ордер: %s", str(e)
                )

            return order_info

        except Exception as e:
            logger.error(
                "Ошибка исполнения сигнала %s: %s",
                symbol, str(e), exc_info=True
            )
            return None

    async def check_and_update_orders(self):
        """Проверить и обновить статусы активных ордеров."""
        for order_id, order_info in list(self.active_orders.items()):
            try:
                symbol = order_info['symbol']
                order = await self.exchange_adapter.async_exchange.fetch_order(
                    order_id, symbol
                )

                status = order.get('status')
                order_info['status'] = status

                # Если ордер исполнен, обновляем статистику
                if status == 'closed' and order_info.get('status') != 'closed':
                    await self._handle_filled_order(order_info, order)

            except Exception as e:
                logger.error(
                    "Ошибка проверки ордера %s: %s",
                    order_id, str(e), exc_info=True
                )

    async def _handle_filled_order(
        self,
        order_info: Dict,
        order_data: Dict
    ):
        """Обработать исполненный ордер."""
        filled_price = order_data.get('average', order_info['entry_price'])
        filled_amount = order_data.get('filled', 0)

        order_info['filled_price'] = filled_price
        order_info['filled_amount'] = filled_amount
        order_info['filled_at'] = datetime.now()

        # Добавляем в историю сделок
        self.executed_trades.append(order_info.copy())

        logger.info(
            "Ордер исполнен: %s %s @ %.2f",
            order_info['symbol'],
            order_info['type'],
            filled_price
        )

    async def update_trailing_stops(self):
        """Обновить трейлинг-стопы для активных позиций."""
        for order_id, order_info in self.active_orders.items():
            if order_info['status'] != 'closed':
                continue

            try:
                # Получаем текущую цену
                ticker = await self.exchange_adapter.fetch_ticker(
                    order_info['symbol']
                )
                current_price = ticker.get('last', 0)

                if current_price == 0:
                    continue

                # Рассчитываем новый стоп-лосс
                new_stop_loss = (
                    self.risk_manager.calculate_trailing_stop(
                        entry_price=order_info['entry_price'],
                        current_price=current_price,
                        current_stop_loss=order_info['stop_loss'],
                        is_long=order_info['is_long']
                    )
                )

                if new_stop_loss:
                    # Отменяем старый стоп-лосс
                    if order_info.get('stop_loss_order_id'):
                        await self.exchange_adapter.cancel_order(
                            order_info['stop_loss_order_id'],
                            order_info['symbol']
                        )

                    # Создаем новый стоп-лосс
                    stop_side = (
                        'sell' if order_info['is_long'] else 'buy'
                    )
                    stop_order = await (
                        self.exchange_adapter.create_stop_loss_order(
                            symbol=order_info['symbol'],
                            side=stop_side,
                            amount=order_info['position_size'] /
                            order_info['entry_price'],
                            stop_price=new_stop_loss
                        )
                    )
                    order_info['stop_loss_order_id'] = stop_order.get('id')
                    order_info['stop_loss'] = new_stop_loss

                    logger.info(
                        "Обновлен трейлинг-стоп для %s: %.2f",
                        order_info['symbol'], new_stop_loss
                    )

            except Exception as e:
                logger.error(
                    "Ошибка обновления трейлинг-стопа для %s: %s",
                    order_id, str(e), exc_info=True
                )

    async def check_partial_closes(self):
        """Проверить и выполнить частичное закрытие позиций."""
        for order_id, order_info in self.active_orders.items():
            if order_info['status'] != 'closed':
                continue

            try:
                # Получаем текущую цену
                ticker = await self.exchange_adapter.fetch_ticker(
                    order_info['symbol']
                )
                current_price = ticker.get('last', 0)

                if current_price == 0:
                    continue

                # Проверяем, нужно ли частично закрыть
                should_close, close_pct = (
                    self.risk_manager.should_partial_close(
                        entry_price=order_info['entry_price'],
                        current_price=current_price,
                        is_long=order_info['is_long']
                    )
                )

                if should_close and not order_info.get('partial_closed'):
                    # Выполняем частичное закрытие
                    close_amount = (
                        order_info['filled_amount'] * (close_pct / 100.0)
                    )
                    side = 'sell' if order_info['is_long'] else 'buy'

                    close_order = await (
                        self.exchange_adapter.create_market_order(
                            symbol=order_info['symbol'],
                            side=side,
                            amount=close_amount
                        )
                    )

                    order_info['partial_closed'] = True
                    order_info['partial_close_pct'] = close_pct
                    order_info['partial_close_order_id'] = (
                        close_order.get('id')
                    )

                    logger.info(
                        "Выполнено частичное закрытие %s%% для %s",
                        close_pct, order_info['symbol']
                    )

            except Exception as e:
                logger.error(
                    "Ошибка проверки частичного закрытия для %s: %s",
                    order_id, str(e), exc_info=True
                )

    async def close(self):
        """Закрыть все соединения."""
        await self.exchange_adapter.close()

