"""
Система отслеживания профитов для торговых сигналов.
Отслеживает P&L, статус сигналов и статистику.
"""
import logging
import json
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from api.models import SignalModel
from utils.market_data_manager import MarketDataManager

logger = logging.getLogger(__name__)


class ProfitTracker:
    """
    Отслеживает профиты и убытки для активных сигналов.
    """
    
    def __init__(
        self,
        data_manager: Optional[MarketDataManager] = None,
        storage_path: Optional[Path] = None
    ):
        """
        Инициализация трекера профитов.
        
        Args:
            data_manager: Менеджер данных рынка
            storage_path: Путь для сохранения данных
        """
        self.data_manager = data_manager or MarketDataManager()
        
        # Путь для хранения данных
        if storage_path is None:
            storage_path = Path(__file__).parent.parent / "data" / "signals"
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Файл для хранения активных сигналов
        self.signals_file = self.storage_path / "active_signals.json"
        self.history_file = self.storage_path / "signals_history.json"
        
        # Загружаем активные сигналы
        self.active_signals: dict[str, dict] = self._load_active_signals()
        
        # Статистика
        self.stats = {
            'total_signals': 0,
            'active_signals': 0,
            'closed_signals': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0
        }
    
    def add_signal(self, signal: SignalModel) -> str:
        """
        Добавляет сигнал для отслеживания.
        
        Args:
            signal: Объект сигнала
            
        Returns:
            ID сигнала
        """
        signal_id = self._generate_signal_id(signal)
        
        # Получаем актуальную цену при добавлении сигнала
        try:
            import ccxt
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            ticker = exchange.fetch_ticker(signal.symbol)
            initial_price = ticker.get('last', signal.entry_price) if ticker else signal.entry_price
        except Exception:
            initial_price = signal.entry_price
        
        signal_data = {
            'id': signal_id,
            'symbol': signal.symbol,
            'type': signal.type,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'confluence': signal.confluence,
            'confidence': signal.confidence,
            'timeframe': signal.timeframe,
            'indicators': signal.indicators,
            'timestamp': signal.timestamp.isoformat(),
            'status': 'active',
            'current_price': initial_price,  # Используем актуальную цену
            'pnl': 0.0,
            'pnl_percent': 0.0,
            'closed_at': None,
            'close_reason': None
        }
        
        self.active_signals[signal_id] = signal_data
        self._save_active_signals()
        
        logger.info(f"Добавлен сигнал для отслеживания: {signal_id}")
        return signal_id
    
    def update_signal_price(self, signal_id: str, current_price: float) -> Optional[dict]:
        """
        Обновляет текущую цену для сигнала и пересчитывает P&L.
        
        Args:
            signal_id: ID сигнала
            current_price: Текущая цена
            
        Returns:
            Обновленные данные сигнала или None
        """
        if signal_id not in self.active_signals:
            return None
        
        signal = self.active_signals[signal_id]
        signal['current_price'] = current_price
        
        # Расчет P&L
        entry_price = signal['entry_price']
        signal_type = signal['type']
        
        if signal_type == "LONG":
            pnl = current_price - entry_price
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl = entry_price - current_price
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
        
        signal['pnl'] = pnl
        signal['pnl_percent'] = pnl_percent
        
        # Проверка на достижение SL или TP
        stop_loss = signal.get('stop_loss')
        take_profit = signal.get('take_profit')
        
        if stop_loss and take_profit:
            if signal_type == "LONG":
                if current_price <= stop_loss:
                    self._close_signal(signal_id, 'stop_loss', current_price)
                elif current_price >= take_profit:
                    self._close_signal(signal_id, 'take_profit', current_price)
            else:  # SHORT
                if current_price >= stop_loss:
                    self._close_signal(signal_id, 'stop_loss', current_price)
                elif current_price <= take_profit:
                    self._close_signal(signal_id, 'take_profit', current_price)
        
        self._save_active_signals()
        return signal
    
    def _close_signal(self, signal_id: str, reason: str, close_price: float):
        """Закрывает сигнал и перемещает в историю."""
        if signal_id not in self.active_signals:
            return
        
        signal = self.active_signals[signal_id]
        signal['status'] = 'closed'
        signal['closed_at'] = datetime.now().isoformat()
        signal['close_reason'] = reason
        signal['close_price'] = close_price
        
        # Пересчитываем финальный P&L
        entry_price = signal['entry_price']
        signal_type = signal['type']
        
        if signal_type == "LONG":
            pnl = close_price - entry_price
            pnl_percent = ((close_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl = entry_price - close_price
            pnl_percent = ((entry_price - close_price) / entry_price) * 100
        
        signal['pnl'] = pnl
        signal['pnl_percent'] = pnl_percent
        
        # Сохраняем в историю
        self._save_to_history(signal)
        
        # Удаляем из активных
        del self.active_signals[signal_id]
        self._save_active_signals()
        
        logger.info(
            f"Сигнал {signal_id} закрыт: {reason}, P&L: {pnl_percent:.2f}%"
        )
    
    def get_active_signals(self) -> list[dict]:
        """Возвращает список активных сигналов."""
        return list(self.active_signals.values())
    
    def get_signal(self, signal_id: str) -> Optional[dict]:
        """Возвращает данные сигнала по ID."""
        return self.active_signals.get(signal_id)
    
    def get_statistics(self) -> dict:
        """Возвращает статистику по сигналам."""
        # Загружаем историю для расчета статистики
        history = self._load_history()
        
        if not history:
            return {
                **self.stats,
                'active_signals': len(self.active_signals)
            }
        
        total = len(history)
        profitable = [s for s in history if s.get('pnl', 0) > 0]
        losing = [s for s in history if s.get('pnl', 0) < 0]
        
        total_profit = sum(s.get('pnl', 0) for s in profitable)
        total_loss = abs(sum(s.get('pnl', 0) for s in losing))
        
        win_rate = (len(profitable) / total * 100) if total > 0 else 0
        avg_profit = (total_profit / len(profitable)) if profitable else 0
        avg_loss = (total_loss / len(losing)) if losing else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
        
        return {
            'total_signals': total,
            'active_signals': len(self.active_signals),
            'closed_signals': total,
            'winning_signals': len(profitable),
            'losing_signals': len(losing),
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': total_profit - total_loss,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    def update_all_prices(self):
        """Обновляет цены для всех активных сигналов."""
        for signal_id, signal in list(self.active_signals.items()):
            try:
                symbol = signal['symbol']
                
                # Получаем актуальную цену напрямую, обходя кэш
                try:
                    import ccxt
                    exchange = ccxt.binance({
                        'enableRateLimit': True,
                        'options': {'defaultType': 'spot'}
                    })
                    ticker = exchange.fetch_ticker(symbol)
                    current_price = ticker.get('last', 0) if ticker else 0
                except Exception:
                    # Fallback на data_manager
                    ticker = self.data_manager.get_ticker(symbol, 'binance')
                    current_price = ticker.get('last', 0) if ticker else 0
                
                if current_price > 0:
                    self.update_signal_price(signal_id, current_price)
                else:
                    logger.warning(f"Не удалось получить цену для {symbol}")
            except Exception as e:
                logger.error(f"Ошибка обновления цены для {signal_id}: {e}", exc_info=True)
    
    def _generate_signal_id(self, signal: SignalModel) -> str:
        """Генерирует уникальный ID для сигнала."""
        timestamp = signal.timestamp.timestamp()
        return f"{signal.symbol}_{signal.type}_{int(timestamp)}"
    
    def _load_active_signals(self) -> dict:
        """Загружает активные сигналы из файла."""
        if not self.signals_file.exists():
            return {}
        
        try:
            with open(self.signals_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Фильтруем только активные сигналы
                return {
                    k: v for k, v in data.items()
                    if v.get('status') == 'active'
                }
        except Exception as e:
            logger.error(f"Ошибка загрузки активных сигналов: {e}")
            return {}
    
    def _save_active_signals(self):
        """Сохраняет активные сигналы в файл."""
        try:
            with open(self.signals_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_signals, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения активных сигналов: {e}")
    
    def _load_history(self) -> list[dict]:
        """Загружает историю сигналов."""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки истории: {e}")
            return []
    
    def _save_to_history(self, signal: dict):
        """Сохраняет сигнал в историю."""
        history = self._load_history()
        history.append(signal)
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения в историю: {e}")

