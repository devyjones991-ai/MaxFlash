"""
Сервис для получения и обработки торговых сигналов.
Интегрирует SignalGenerator и ProfitTracker для веб-интерфейса.
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalsService:
    """Сервис для работы с сигналами в веб-интерфейсе."""

    def __init__(
        self,
        signal_generator=None,
        profit_tracker=None
    ):
        """
        Инициализация сервиса сигналов.

        Args:
            signal_generator: Экземпляр SignalGenerator
            profit_tracker: Экземпляр ProfitTracker
        """
        self.signal_generator = signal_generator
        self.profit_tracker = profit_tracker

    def get_signals_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Получить сигналы для указанного символа.

        Args:
            symbol: Торговая пара (например, BTC/USDT)

        Returns:
            Список сигналов в формате для веб-интерфейса
        """
        if not self.signal_generator:
            logger.warning("SignalGenerator не инициализирован")
            return []

        try:
            # Генерируем сигналы для символа
            signals = self.signal_generator.generate_signals(symbol)
            
            # Преобразуем в формат для веб-интерфейса
            web_signals = []
            for signal in signals:
                web_signal = {
                    "symbol": signal.symbol,
                    "type": signal.type,
                    "strength": (
                        "Strong" if signal.confidence >= 0.8
                        else "Medium" if signal.confidence >= 0.6
                        else "Weak"
                    ),
                    "confluence": signal.confluence,
                    "zone": signal.entry_price,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "risk_reward": (
                        abs((signal.take_profit - signal.entry_price) /
                            (signal.entry_price - signal.stop_loss))
                        if signal.stop_loss and signal.take_profit
                        else 0.0
                    ),
                    "timeframe": signal.timeframe,
                    "timestamp": signal.timestamp,
                    "confidence": signal.confidence,
                    "indicators": signal.indicators
                }
                web_signals.append(web_signal)
            
            logger.debug("Получено %s сигналов для %s", len(web_signals), symbol)
            return web_signals
            
        except Exception as e:
            logger.error("Ошибка получения сигналов для %s: %s", symbol, str(e), exc_info=True)
            return []

    def get_active_signals(self) -> List[Dict[str, Any]]:
        """
        Получить все активные сигналы с актуальными ценами и P&L.

        Returns:
            Список активных сигналов с P&L
        """
        if not self.profit_tracker:
            logger.warning("ProfitTracker не инициализирован")
            return []

        try:
            # Обновляем цены перед получением
            self.profit_tracker.update_all_prices()
            
            # Получаем активные сигналы
            active_signals = self.profit_tracker.get_active_signals()
            
            # Преобразуем в формат для веб-интерфейса
            web_signals = []
            for signal_data in active_signals:
                signal_type = signal_data.get('type', 'LONG')
                entry_price = signal_data.get('entry_price', 0)
                current_price = signal_data.get('current_price', entry_price)
                pnl_percent = signal_data.get('pnl_percent', 0)
                
                web_signal = {
                    "symbol": signal_data.get('symbol', 'N/A'),
                    "type": signal_type,
                    "strength": (
                        "Strong" if signal_data.get('confidence', 0) >= 0.8
                        else "Medium" if signal_data.get('confidence', 0) >= 0.6
                        else "Weak"
                    ),
                    "confluence": signal_data.get('confluence', 0),
                    "zone": entry_price,
                    "entry": entry_price,
                    "current_price": current_price,
                    "stop_loss": signal_data.get('stop_loss', 0),
                    "take_profit": signal_data.get('take_profit', 0),
                    "pnl": signal_data.get('pnl', 0),
                    "pnl_percent": pnl_percent,
                    "risk_reward": (
                        abs((signal_data.get('take_profit', 0) - entry_price) /
                            (entry_price - signal_data.get('stop_loss', 1)))
                        if signal_data.get('stop_loss') and signal_data.get('take_profit')
                        else 0.0
                    ),
                    "timeframe": signal_data.get('timeframe', '15m'),
                    "timestamp": (
                        datetime.fromisoformat(signal_data['timestamp'])
                        if isinstance(signal_data.get('timestamp'), str)
                        else signal_data.get('timestamp', datetime.now())
                    ),
                    "confidence": signal_data.get('confidence', 0),
                    "indicators": signal_data.get('indicators', []),
                    "status": signal_data.get('status', 'active')
                }
                web_signals.append(web_signal)
            
            logger.debug("Получено %s активных сигналов", len(web_signals))
            return web_signals
            
        except Exception as e:
            logger.error("Ошибка получения активных сигналов: %s", str(e), exc_info=True)
            return []

    def get_all_signals_for_dashboard(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Получить все сигналы для dashboard (новые + активные).

        Args:
            symbol: Торговая пара для генерации новых сигналов

        Returns:
            Объединенный список сигналов
        """
        # Получаем новые сигналы для символа
        new_signals = self.get_signals_for_symbol(symbol)
        
        # Получаем активные сигналы
        active_signals = self.get_active_signals()
        
        # Объединяем, убирая дубликаты по symbol+type
        all_signals = {}
        
        # Сначала добавляем активные (они имеют приоритет с P&L)
        for signal in active_signals:
            key = f"{signal['symbol']}_{signal['type']}"
            all_signals[key] = signal
        
        # Затем добавляем новые, если их еще нет
        for signal in new_signals:
            key = f"{signal['symbol']}_{signal['type']}"
            if key not in all_signals:
                all_signals[key] = signal
        
        return list(all_signals.values())


# Глобальный экземпляр сервиса
_signals_service_instance: Optional[SignalsService] = None


def get_signals_service(
    signal_generator=None,
    profit_tracker=None
) -> SignalsService:
    """
    Получить или создать экземпляр SignalsService (singleton).

    Args:
        signal_generator: Экземпляр SignalGenerator
        profit_tracker: Экземпляр ProfitTracker

    Returns:
        Экземпляр SignalsService
    """
    global _signals_service_instance

    if _signals_service_instance is None:
        _signals_service_instance = SignalsService(
            signal_generator=signal_generator,
            profit_tracker=profit_tracker
        )
    else:
        # Обновляем ссылки если они переданы
        if signal_generator:
            _signals_service_instance.signal_generator = signal_generator
        if profit_tracker:
            _signals_service_instance.profit_tracker = profit_tracker

    return _signals_service_instance

