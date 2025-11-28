"""
Система генерации торговых сигналов на основе Smart Money Concepts.
Генерирует сигналы с entry, stop loss, take profit и отслеживает их.
"""
import logging
from typing import Optional
from datetime import datetime
import pandas as pd

from api.models import SignalModel
from utils.market_data_manager import MarketDataManager
from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.smart_money.fair_value_gaps import FairValueGapDetector
from indicators.smart_money.market_structure import MarketStructureAnalyzer
from indicators.volume_profile.volume_profile import VolumeProfileCalculator
from indicators.market_profile.market_profile import MarketProfileCalculator
from indicators.footprint.delta import DeltaAnalyzer
from utils.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Генератор торговых сигналов на основе Smart Money Concepts.
    """
    
    def __init__(
        self,
        data_manager: Optional[MarketDataManager] = None,
        min_confidence: float = 0.6,
        min_confluence: int = 3
    ):
        """
        Инициализация генератора сигналов.
        
        Args:
            data_manager: Менеджер данных рынка
            min_confidence: Минимальная уверенность сигнала (0-1)
            min_confluence: Минимальное количество подтверждающих сигналов
        """
        self.data_manager = data_manager or MarketDataManager()
        self.min_confidence = min_confidence
        self.min_confluence = min_confluence
        
        # Инициализация детекторов
        self.ob_detector = OrderBlockDetector()
        self.fvg_detector = FairValueGapDetector()
        self.market_structure = MarketStructureAnalyzer()
        self.vp_calculator = VolumeProfileCalculator()
        self.mp_calculator = MarketProfileCalculator()
        self.delta_analyzer = DeltaAnalyzer()
        self.risk_manager = RiskManager(risk_per_trade=0.01)
        
        # Кэш для активных сигналов
        self.active_signals: dict[str, SignalModel] = {}
    
    def generate_signals(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 200
    ) -> list[SignalModel]:
        """
        Генерирует торговые сигналы для указанной пары.
        
        Args:
            symbol: Торговая пара (например, BTC/USDT)
            timeframe: Таймфрейм
            limit: Количество свечей для анализа
            
        Returns:
            Список сигналов
        """
        try:
            # Загружаем данные
            df = self.data_manager.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                exchange_id='binance'
            )
            
            if df is None or df.empty:
                logger.warning(f"Нет данных для {symbol}")
                return []
            
            # Вычисляем индикаторы
            df = self._calculate_indicators(df)
            
            # Генерируем сигналы
            signals = self._analyze_and_generate_signals(df, symbol, timeframe)
            
            # Фильтруем по минимальной уверенности
            filtered_signals = [
                s for s in signals
                if s.confidence >= self.min_confidence
            ]
            
            logger.info(
                f"Сгенерировано {len(filtered_signals)} сигналов для {symbol}"
            )
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Ошибка генерации сигналов для {symbol}: {e}", exc_info=True)
            return []
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Вычисляет все необходимые индикаторы."""
        try:
            # Smart Money Concepts
            df = self.ob_detector.detect_order_blocks(df)
            df = self.fvg_detector.detect_fair_value_gaps(df)
            df = self.market_structure.analyze_market_structure(df)
            
            # Volume Profile
            df = self.vp_calculator.calculate_volume_profile(df, period=20)
            
            # Market Profile
            df = self.mp_calculator.calculate_market_profile(df)
            
            # Delta
            df = self.delta_analyzer.calculate_delta(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка вычисления индикаторов: {e}")
            return df
    
    def _analyze_and_generate_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> List[SignalModel]:
        """Анализирует данные и генерирует сигналы."""
        signals = []
        
        if len(df) < 50:
            return signals
        
        # Берем последние 10 свечей для анализа
        recent_data = df.tail(10)
        current_candle = df.iloc[-1]
        current_price = current_candle['close']
        
        # Анализ для LONG сигналов
        long_signal = self._check_long_conditions(
            current_candle, recent_data, current_price
        )
        if long_signal:
            signal = self._create_signal(
                symbol=symbol,
                signal_type="LONG",
                entry_price=current_price,
                current_candle=current_candle,
                recent_data=recent_data,
                indicators=long_signal['indicators'],
                confluence=long_signal['confluence']
            )
            if signal:
                signals.append(signal)
        
        # Анализ для SHORT сигналов
        short_signal = self._check_short_conditions(
            current_candle, recent_data, current_price
        )
        if short_signal:
            signal = self._create_signal(
                symbol=symbol,
                signal_type="SHORT",
                entry_price=current_price,
                current_candle=current_candle,
                recent_data=recent_data,
                indicators=short_signal['indicators'],
                confluence=short_signal['confluence']
            )
            if signal:
                signals.append(signal)
        
        return signals
    
    def _check_long_conditions(
        self,
        current_candle: pd.Series,
        recent_data: pd.DataFrame,
        current_price: float
    ) -> Optional[Dict]:
        """Проверяет условия для LONG сигнала."""
        indicators = []
        confluence = 0
        
        # 1. Проверка Order Block (bullish)
        if pd.notna(current_candle.get('ob_bullish_low')):
            ob_low = current_candle['ob_bullish_low']
            ob_high = current_candle['ob_bullish_high']
            if ob_low <= current_price <= ob_high:
                indicators.append("Order Block")
                confluence += 1
        
        # 2. Проверка FVG (bullish)
        if pd.notna(current_candle.get('fvg_bullish_low')):
            fvg_low = current_candle['fvg_bullish_low']
            fvg_high = current_candle['fvg_bullish_high']
            if fvg_low <= current_price <= fvg_high:
                indicators.append("Fair Value Gap")
                confluence += 1
        
        # 3. Проверка Volume Profile POC
        if pd.notna(current_candle.get('vp_poc')):
            poc = current_candle['vp_poc']
            # Если цена близка к POC (в пределах 1%)
            if abs(current_price - poc) / poc < 0.01:
                indicators.append("Volume Profile POC")
                confluence += 1
        
        # 4. Проверка Market Profile Value Area
        if pd.notna(current_candle.get('mp_val')):
            val = current_candle['mp_val']
            vah = current_candle.get('mp_vah', current_price * 1.1)
            if val <= current_price <= vah:
                indicators.append("Market Profile Value Area")
                confluence += 1
        
        # 5. Проверка Delta (положительный)
        if pd.notna(current_candle.get('delta')):
            delta = current_candle['delta']
            if delta > 0:
                indicators.append("Positive Delta")
                confluence += 1
        
        # 6. Проверка Market Structure (bullish trend)
        market_structure = current_candle.get('market_structure', '')
        if 'bullish' in str(market_structure).lower():
            indicators.append("Bullish Market Structure")
            confluence += 1
        
        if confluence >= self.min_confluence:
            return {
                'indicators': indicators,
                'confluence': confluence
            }
        
        return None
    
    def _check_short_conditions(
        self,
        current_candle: pd.Series,
        recent_data: pd.DataFrame,
        current_price: float
    ) -> Optional[Dict]:
        """Проверяет условия для SHORT сигнала."""
        indicators = []
        confluence = 0
        
        # 1. Проверка Order Block (bearish)
        if pd.notna(current_candle.get('ob_bearish_low')):
            ob_low = current_candle['ob_bearish_low']
            ob_high = current_candle['ob_bearish_high']
            if ob_low <= current_price <= ob_high:
                indicators.append("Order Block")
                confluence += 1
        
        # 2. Проверка FVG (bearish)
        if pd.notna(current_candle.get('fvg_bearish_low')):
            fvg_low = current_candle['fvg_bearish_low']
            fvg_high = current_candle['fvg_bearish_high']
            if fvg_low <= current_price <= fvg_high:
                indicators.append("Fair Value Gap")
                confluence += 1
        
        # 3. Проверка Volume Profile POC
        if pd.notna(current_candle.get('vp_poc')):
            poc = current_candle['vp_poc']
            if abs(current_price - poc) / poc < 0.01:
                indicators.append("Volume Profile POC")
                confluence += 1
        
        # 4. Проверка Market Profile Value Area
        if pd.notna(current_candle.get('mp_val')):
            val = current_candle['mp_val']
            vah = current_candle.get('mp_vah', current_price * 1.1)
            if val <= current_price <= vah:
                indicators.append("Market Profile Value Area")
                confluence += 1
        
        # 5. Проверка Delta (отрицательный)
        if pd.notna(current_candle.get('delta')):
            delta = current_candle['delta']
            if delta < 0:
                indicators.append("Negative Delta")
                confluence += 1
        
        # 6. Проверка Market Structure (bearish trend)
        market_structure = current_candle.get('market_structure', '')
        if 'bearish' in str(market_structure).lower():
            indicators.append("Bearish Market Structure")
            confluence += 1
        
        if confluence >= self.min_confluence:
            return {
                'indicators': indicators,
                'confluence': confluence
            }
        
        return None
    
    def _create_signal(
        self,
        symbol: str,
        signal_type: str,
        entry_price: float,
        current_candle: pd.Series,
        recent_data: pd.DataFrame,
        indicators: List[str],
        confluence: int
    ) -> Optional[SignalModel]:
        """Создает объект сигнала с расчетом SL и TP."""
        try:
            # Расчет ATR для определения SL и TP
            atr = current_candle.get('atr', entry_price * 0.02)  # 2% по умолчанию
            
            # Если ATR не рассчитан, используем процент от цены
            if pd.isna(atr) or atr == 0:
                atr = entry_price * 0.02
            
            # Расчет Stop Loss и Take Profit
            if signal_type == "LONG":
                # SL ниже Order Block или на 1.5 ATR
                stop_loss = entry_price - (atr * 1.5)
                
                # Проверяем Order Block для более точного SL
                if pd.notna(current_candle.get('ob_bullish_low')):
                    ob_low = current_candle['ob_bullish_low']
                    stop_loss = min(stop_loss, ob_low * 0.999)
                
                # TP на 2-3 ATR или до следующего уровня сопротивления
                take_profit = entry_price + (atr * 2.5)
                
                # Проверяем Volume Profile уровни
                if pd.notna(current_candle.get('vp_vah')):
                    vah = current_candle['vp_vah']
                    if vah > entry_price:
                        take_profit = min(take_profit, vah * 0.999)
                
            else:  # SHORT
                # SL выше Order Block или на 1.5 ATR
                stop_loss = entry_price + (atr * 1.5)
                
                # Проверяем Order Block для более точного SL
                if pd.notna(current_candle.get('ob_bearish_high')):
                    ob_high = current_candle['ob_bearish_high']
                    stop_loss = max(stop_loss, ob_high * 1.001)
                
                # TP на 2-3 ATR или до следующего уровня поддержки
                take_profit = entry_price - (atr * 2.5)
                
                # Проверяем Volume Profile уровни
                if pd.notna(current_candle.get('vp_val')):
                    val = current_candle['vp_val']
                    if val < entry_price:
                        take_profit = max(take_profit, val * 1.001)
            
            # Расчет уверенности на основе confluence
            confidence = min(0.5 + (confluence * 0.1), 0.95)
            
            # Создаем сигнал
            signal = SignalModel(
                symbol=symbol,
                type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confluence=confluence,
                timeframe=current_candle.get('timeframe', '15m') if 'timeframe' in current_candle else '15m',
                indicators=indicators,
                confidence=confidence,
                timestamp=datetime.now()
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка создания сигнала: {e}")
            return None
    
    def get_active_signals(self) -> List[SignalModel]:
        """Возвращает список активных сигналов."""
        return list(self.active_signals.values())
    
    def add_active_signal(self, signal: SignalModel):
        """Добавляет сигнал в активные."""
        signal_id = f"{signal.symbol}_{signal.type}_{signal.timestamp.timestamp()}"
        self.active_signals[signal_id] = signal
    
    def remove_active_signal(self, signal_id: str):
        """Удаляет сигнал из активных."""
        if signal_id in self.active_signals:
            del self.active_signals[signal_id]

