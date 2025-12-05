"""
Независимый сканер сигналов для топ-50 монет.
Работает по своим настройкам, не привязан к графику дашборда.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import pandas as pd
import numpy as np

from utils.market_data_manager import MarketDataManager

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Торговый сигнал."""
    symbol: str
    signal_type: str  # LONG или SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    timeframe: str
    indicators: List[str]
    timestamp: datetime
    
    @property
    def risk_reward(self) -> float:
        """Расчёт Risk/Reward."""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk if risk > 0 else 0


class SignalScanner:
    """
    Независимый сканер сигналов.
    Сканирует все монеты по своим настройкам.
    """
    
    # Собственные настройки сканера (не зависят от графика!)
    SCANNER_SETTINGS = {
        'timeframe': '15m',           # Таймфрейм для сканирования
        'exchange': 'binance',         # Биржа
        'min_volume_usd': 1_000_000,   # Минимальный объём за 24ч
        'min_confidence': 0.22,        # Минимальная уверенность (2 из 9 подтверждений)
        'rsi_oversold': 35,            # RSI перепроданность (ослаблено с 30)
        'rsi_overbought': 65,          # RSI перекупленность (ослаблено с 70)
        'ema_fast': 9,                 # Быстрая EMA
        'ema_slow': 21,                # Медленная EMA
        'atr_multiplier_sl': 1.5,      # ATR множитель для SL
        'atr_multiplier_tp': 2.5,      # ATR множитель для TP
    }
    
    # Топ-50 монет
    COINS = [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
        "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT",
        "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "NEAR/USDT",
        "APT/USDT", "ARB/USDT", "OP/USDT", "TIA/USDT", "FIL/USDT",
        "ICP/USDT", "STX/USDT", "IMX/USDT", "HBAR/USDT", "INJ/USDT",
        "VET/USDT", "SUI/USDT", "SEI/USDT", "RUNE/USDT", "MKR/USDT",
        "AAVE/USDT", "GRT/USDT", "FTM/USDT", "ALGO/USDT", "ETC/USDT",
        "THETA/USDT", "XLM/USDT", "FLOW/USDT", "EOS/USDT", "SAND/USDT",
        "MANA/USDT", "AXS/USDT", "KAVA/USDT", "WLD/USDT", "PEPE/USDT",
        "FET/USDT", "GALA/USDT", "CHZ/USDT", "ZIL/USDT", "ENJ/USDT"
    ]
    
    def __init__(self, data_manager: Optional[MarketDataManager] = None):
        self.data_manager = data_manager or MarketDataManager()
        self._signals_cache: List[Signal] = []
        self._last_scan: Optional[datetime] = None
    
    def scan_all(self, coins: Optional[List[str]] = None) -> List[Signal]:
        """
        Сканирует все монеты и возвращает сигналы.
        
        Args:
            coins: Список монет для сканирования (по умолчанию все 50)
            
        Returns:
            Список найденных сигналов, отсортированных по уверенности
        """
        coins = coins or self.COINS
        signals = []
        
        logger.info(f"Начинаю сканирование {len(coins)} монет...")
        
        for symbol in coins:
            try:
                signal = self.analyze_coin(symbol)
                if signal:
                    signals.append(signal)
                    logger.info(f"✅ Найден сигнал: {signal.signal_type} {symbol} @ {signal.entry_price:.4f}")
            except Exception as e:
                logger.debug(f"Ошибка анализа {symbol}: {e}")
                continue
        
        # Сортируем по уверенности
        signals.sort(key=lambda s: s.confidence, reverse=True)
        
        # Кэшируем результаты
        self._signals_cache = signals
        self._last_scan = datetime.now()
        
        logger.info(f"Сканирование завершено. Найдено {len(signals)} сигналов.")
        
        return signals
    
    def analyze_coin(self, symbol: str) -> Optional[Signal]:
        """
        Анализирует одну монету и возвращает сигнал если есть.
        
        Условия для сигнала:
        - RSI в зоне перекупленности/перепроданности
        - EMA crossover
        - Подтверждение объёмом
        - MACD дивергенция
        """
        settings = self.SCANNER_SETTINGS
        
        # Получаем данные
        df = self.data_manager.get_ohlcv(
            symbol=symbol,
            timeframe=settings['timeframe'],
            limit=100,
            exchange_id=settings['exchange']
        )
        
        if df is None or len(df) < 50:
            return None
        
        # Вычисляем индикаторы
        df = self._calculate_indicators(df)
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Проверяем условия
        long_signal = self._check_long(df, current, prev)
        short_signal = self._check_short(df, current, prev)
        
        # Логируем для отладки
        rsi = current.get('rsi', 0)
        ema_fast = current.get('ema_fast', 0)
        ema_slow = current.get('ema_slow', 0)
        logger.debug(f"{symbol}: RSI={rsi:.1f}, EMA_F={ema_fast:.2f}, EMA_S={ema_slow:.2f}")
        
        if long_signal:
            logger.info(f"{symbol} LONG: conf={long_signal['confidence']:.2f}, indicators={long_signal['indicators']}")
            if long_signal['confidence'] >= settings['min_confidence']:
                return self._create_signal(symbol, "LONG", df, long_signal)
        
        if short_signal:
            logger.info(f"{symbol} SHORT: conf={short_signal['confidence']:.2f}, indicators={short_signal['indicators']}")
            if short_signal['confidence'] >= settings['min_confidence']:
                return self._create_signal(symbol, "SHORT", df, short_signal)
        
        return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Вычисляет технические индикаторы."""
        settings = self.SCANNER_SETTINGS
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA
        df['ema_fast'] = df['close'].ewm(span=settings['ema_fast'], adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=settings['ema_slow'], adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # MACD
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        
        # Volume SMA
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        # Stochastic
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        return df
    
    def _check_long(self, df: pd.DataFrame, current: pd.Series, prev: pd.Series) -> Optional[Dict]:
        """
        Проверяет условия для LONG сигнала.
        Комбинированный подход: текущее состояние + подтверждение тренда.
        Требуется минимум 3 подтверждения.
        """
        indicators = []
        confirmations = 0
        
        # === СОСТОЯНИЕ ИНДИКАТОРОВ (текущие значения) ===
        
        # 1. RSI в зоне покупки (< 55, идеально < 40)
        rsi = current['rsi']
        if pd.notna(rsi):
            if rsi < 30:
                indicators.append("RSI Oversold (<30)")
                confirmations += 2
            elif rsi < 40:
                indicators.append("RSI Low (<40)")
                confirmations += 1.5
            elif rsi < 50:
                indicators.append("RSI Neutral-Low (<50)")
                confirmations += 1
            elif rsi < 55:
                indicators.append("RSI Near-Neutral")
                confirmations += 0.5
        
        # 2. EMA выравнивание (fast > slow = бычий тренд)
        if pd.notna(current['ema_fast']) and pd.notna(current['ema_slow']):
            if current['ema_fast'] > current['ema_slow']:
                indicators.append("EMA Bullish Alignment")
                confirmations += 1
                # Бонус за недавний crossover
                if prev['ema_fast'] <= prev['ema_slow']:
                    indicators.append("EMA Fresh Crossover")
                    confirmations += 1
        
        # 3. Позиция относительно EMA 200 (тренд)
        if pd.notna(current['ema_200']):
            if current['close'] > current['ema_200']:
                indicators.append("Uptrend (>EMA200)")
                confirmations += 1
            elif current['close'] > current['ema_200'] * 0.98:  # В пределах 2%
                indicators.append("Near EMA200 Support")
                confirmations += 0.5
        
        # 4. MACD состояние
        if pd.notna(current['macd']) and pd.notna(current['macd_signal']):
            if current['macd'] > current['macd_signal']:
                indicators.append("MACD Bullish")
                confirmations += 1
            if pd.notna(current['macd_hist']) and current['macd_hist'] > 0:
                if prev['macd_hist'] <= 0:
                    indicators.append("MACD Histogram Flip")
                    confirmations += 1
        
        # 5. Stochastic состояние
        if pd.notna(current['stoch_k']) and pd.notna(current['stoch_d']):
            if current['stoch_k'] < 30:
                indicators.append("Stoch Oversold")
                confirmations += 1
            elif current['stoch_k'] > current['stoch_d'] and current['stoch_k'] < 50:
                indicators.append("Stoch Bullish Cross")
                confirmations += 0.5
        
        # 6. Bollinger Bands - цена у нижней границы
        if pd.notna(current['bb_lower']):
            if current['close'] <= current['bb_lower'] * 1.01:
                indicators.append("BB Lower Zone")
                confirmations += 1
            elif current['close'] < current['bb_middle']:
                indicators.append("Below BB Middle")
                confirmations += 0.5
        
        # 7. Объём выше среднего (подтверждение)
        if pd.notna(current['volume_sma']) and current['volume_sma'] > 0:
            if current['volume'] > current['volume_sma'] * 1.3:
                indicators.append("Volume Spike")
                confirmations += 0.5
        
        # === ГЕНЕРАЦИЯ СИГНАЛА ===
        # Минимум 2 подтверждения для сигнала (ослаблено для большего количества сигналов)
        if confirmations >= 2 and len(indicators) >= 2:
            # Расчёт confidence
            max_confirmations = 9
            confidence = min(confirmations / max_confirmations, 0.95)
            
            # Бонус за тренд
            if "Uptrend (>EMA200)" in indicators:
                confidence = min(confidence * 1.1, 0.95)
            
            return {
                'indicators': indicators,
                'confidence': confidence,
                'confirmations': confirmations
            }
        
        return None
    
    def _check_short(self, df: pd.DataFrame, current: pd.Series, prev: pd.Series) -> Optional[Dict]:
        """
        Проверяет условия для SHORT сигнала.
        Комбинированный подход: текущее состояние + подтверждение тренда.
        Требуется минимум 3 подтверждения.
        """
        indicators = []
        confirmations = 0
        
        # === СОСТОЯНИЕ ИНДИКАТОРОВ (текущие значения) ===
        
        # 1. RSI в зоне продажи (> 45, идеально > 60)
        rsi = current['rsi']
        if pd.notna(rsi):
            if rsi > 70:
                indicators.append("RSI Overbought (>70)")
                confirmations += 2
            elif rsi > 60:
                indicators.append("RSI High (>60)")
                confirmations += 1.5
            elif rsi > 50:
                indicators.append("RSI Neutral-High (>50)")
                confirmations += 1
            elif rsi > 45:
                indicators.append("RSI Near-Neutral")
                confirmations += 0.5
        
        # 2. EMA выравнивание (fast < slow = медвежий тренд)
        if pd.notna(current['ema_fast']) and pd.notna(current['ema_slow']):
            if current['ema_fast'] < current['ema_slow']:
                indicators.append("EMA Bearish Alignment")
                confirmations += 1
                # Бонус за недавний crossover
                if prev['ema_fast'] >= prev['ema_slow']:
                    indicators.append("EMA Fresh Crossover")
                    confirmations += 1
        
        # 3. Позиция относительно EMA 200 (тренд)
        if pd.notna(current['ema_200']):
            if current['close'] < current['ema_200']:
                indicators.append("Downtrend (<EMA200)")
                confirmations += 1
            elif current['close'] < current['ema_200'] * 1.02:  # В пределах 2%
                indicators.append("Near EMA200 Resistance")
                confirmations += 0.5
        
        # 4. MACD состояние
        if pd.notna(current['macd']) and pd.notna(current['macd_signal']):
            if current['macd'] < current['macd_signal']:
                indicators.append("MACD Bearish")
                confirmations += 1
            if pd.notna(current['macd_hist']) and current['macd_hist'] < 0:
                if prev['macd_hist'] >= 0:
                    indicators.append("MACD Histogram Flip")
                    confirmations += 1
        
        # 5. Stochastic состояние
        if pd.notna(current['stoch_k']) and pd.notna(current['stoch_d']):
            if current['stoch_k'] > 70:
                indicators.append("Stoch Overbought")
                confirmations += 1
            elif current['stoch_k'] < current['stoch_d'] and current['stoch_k'] > 50:
                indicators.append("Stoch Bearish Cross")
                confirmations += 0.5
        
        # 6. Bollinger Bands - цена у верхней границы
        if pd.notna(current['bb_upper']):
            if current['close'] >= current['bb_upper'] * 0.99:
                indicators.append("BB Upper Zone")
                confirmations += 1
            elif current['close'] > current['bb_middle']:
                indicators.append("Above BB Middle")
                confirmations += 0.5
        
        # 7. Объём выше среднего (подтверждение)
        if pd.notna(current['volume_sma']) and current['volume_sma'] > 0:
            if current['volume'] > current['volume_sma'] * 1.3:
                indicators.append("Volume Spike")
                confirmations += 0.5
        
        # === ГЕНЕРАЦИЯ СИГНАЛА ===
        # Минимум 2 подтверждения для сигнала (ослаблено для большего количества сигналов)
        if confirmations >= 2 and len(indicators) >= 2:
            # Расчёт confidence
            max_confirmations = 9
            confidence = min(confirmations / max_confirmations, 0.95)
            
            # Бонус за тренд
            if "Downtrend (<EMA200)" in indicators:
                confidence = min(confidence * 1.1, 0.95)
            
            return {
                'indicators': indicators,
                'confidence': confidence,
                'confirmations': confirmations
            }
        
        return None
    
    def _create_signal(
        self, 
        symbol: str, 
        signal_type: str, 
        df: pd.DataFrame,
        analysis: Dict
    ) -> Signal:
        """Создаёт объект сигнала."""
        settings = self.SCANNER_SETTINGS
        current = df.iloc[-1]
        price = current['close']
        atr = current['atr']
        
        # Если ATR не валидный, используем 2% от цены
        if pd.isna(atr) or atr <= 0:
            atr = price * 0.02
        
        if signal_type == "LONG":
            stop_loss = price - (atr * settings['atr_multiplier_sl'])
            take_profit = price + (atr * settings['atr_multiplier_tp'])
        else:  # SHORT
            stop_loss = price + (atr * settings['atr_multiplier_sl'])
            take_profit = price - (atr * settings['atr_multiplier_tp'])
        
        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=analysis['confidence'],
            timeframe=settings['timeframe'],
            indicators=analysis['indicators'],
            timestamp=datetime.now()
        )
    
    def get_cached_signals(self) -> List[Signal]:
        """Возвращает закэшированные сигналы."""
        return self._signals_cache
    
    def get_last_scan_time(self) -> Optional[datetime]:
        """Возвращает время последнего сканирования."""
        return self._last_scan
    
    def scan_single(self, symbol: str) -> Optional[Signal]:
        """
        Сканирует одну конкретную монету.
        Удобно для кнопки "Получить сигнал".
        """
        return self.analyze_coin(symbol)


# Глобальный экземпляр сканера
_scanner: Optional[SignalScanner] = None


def get_scanner() -> SignalScanner:
    """Получить глобальный экземпляр сканера."""
    global _scanner
    if _scanner is None:
        _scanner = SignalScanner()
    return _scanner

