"""
Enhanced Signal Generator
Unified signal generation logic for dashboard and bot with improved sensitivity
and better support for bearish markets.
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Импорт нового валидатора
try:
    from utils.advanced_signal_validator import AdvancedSignalValidator
    HAS_ADVANCED_VALIDATOR = True
except ImportError:
    HAS_ADVANCED_VALIDATOR = False
    logger.warning("AdvancedSignalValidator not available, using basic validation")


class EnhancedSignalGenerator:
    """
    Enhanced signal generator with:
    - Lower thresholds for more signals
    - Better bear market support (more SELL signals)
    - Adaptive thresholds based on market volatility
    - Unified logic for dashboard and bot
    - Advanced validation with contradiction detection, stats, and deduplication
    """
    
    # Инициализация продвинутого валидатора (singleton pattern)
    _validator_instance = None
    
    @classmethod
    def _get_validator(cls):
        """Получить экземпляр валидатора (singleton)."""
        if HAS_ADVANCED_VALIDATOR:
            if cls._validator_instance is None:
                cls._validator_instance = AdvancedSignalValidator(duplicate_window_minutes=15)
            return cls._validator_instance
        return None
    
    # Configuration - более чувствительные пороги
    CONFIG = {
        'rsi_oversold': 40,        # BUY zone (было 30, теперь шире)
        'rsi_overbought': 60,      # SELL zone (было 70, теперь шире)
        'rsi_buy_zone': 55,        # Максимум RSI для BUY (было 52)
        'rsi_sell_zone': 45,       # Минимум RSI для SELL
        'ma_diff_pct': 0.0015,     # 0.15% разница MA (чувствительнее)
        'volume_spike': 1.2,       # Объем выше среднего (было 1.5)
        'min_score_diff': 10,      # Минимальная разница для сигнала
        'volatility_exclusion': 50, # Исключать только >50% (было 40)
        'change_exclusion': 30,     # Исключать только >30% (было 25)
        'volume_exclusion': 0.3,    # Исключать если объем <30% (было 0.5)
    }
    
    @classmethod
    def critical_validation(cls, signal_direction: str, rsi: float, macd_histogram: float, confidence: float) -> tuple:
        """
        DEPRECATED: Используйте advanced_validation вместо этого.
        Оставлено для обратной совместимости.
        """
        # Используем новый валидатор если доступен
        validator = cls._get_validator()
        if validator:
            # Простая обертка для обратной совместимости
            result = validator.validate(
                symbol="UNKNOWN",
                signal_direction=signal_direction,
                confidence=confidence,
                rsi=rsi,
                macd_histogram=macd_histogram,
                price_change_24h=0.0,
                volume_ratio=1.0
            )
            return (result.signal, result.confidence) if result.signal else (None, 0)
        
        # Fallback к старой логике
        if signal_direction == "HOLD":
            return signal_direction, confidence
        
        if signal_direction == "SELL" and rsi < 35:
            return None, 0
        
        if signal_direction == "BUY" and rsi > 75:
            return None, 0
        
        if signal_direction == "SELL" and macd_histogram > 0.0005:
            return None, 0
        
        return signal_direction, confidence
    
    @staticmethod
    def calculate_rsi(close: pd.Series, period: int = 14) -> float:
        """Calculate RSI for the last candle."""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if len(rsi) > 0 else 50
    
    @staticmethod
    def calculate_macd(close: pd.Series, fast: int = 8, slow: int = 17, signal: int = 9) -> Tuple[float, float, float]:
        """Calculate MACD indicator (8-17-9 for short-term)."""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
    
    @classmethod
    def generate_signal(
        cls,
        ticker: Dict,
        ohlcv_data: Optional[pd.DataFrame] = None
    ) -> Tuple[str, int, List[str]]:
        """
        Generate enhanced trading signal.
        
        Args:
            ticker: Dictionary with ticker data (percentage, quoteVolume, etc.)
            ohlcv_data: OHLCV DataFrame (optional, for better analysis)
        
        Returns:
            Tuple of (signal, confidence_score, reasons_list)
        """
        change_24h = ticker.get('percentage', 0) or 0
        volume_24h = ticker.get('quoteVolume', 0) or 0
        
        # Initialize scores
        buy_score = 0
        sell_score = 0
        reasons = []
        config = cls.CONFIG
        
        # === EXCLUSION CONDITIONS (более мягкие) ===
        if abs(change_24h) > config['change_exclusion']:
            return "HOLD", 30, [f"⚠️ Слишком большое движение {change_24h:+.1f}%"]
        
        # Need OHLCV for detailed analysis
        if ohlcv_data is None or len(ohlcv_data) < 26:
            # Fallback: simple signal based on 24h change only
            if change_24h <= -3:
                return "SELL", 55, [f"📉 Падение {change_24h:+.1f}%"]
            elif change_24h >= 3:
                return "BUY", 55, [f"📈 Рост {change_24h:+.1f}%"]
            else:
                return "HOLD", 40, ["⏳ Недостаточно данных"]
        
        close = ohlcv_data['close']
        volume = ohlcv_data['volume']
        
        # Calculate 4h volatility
        volatility_4h = (close.tail(16).max() - close.tail(16).min()) / close.tail(16).mean() * 100
        if volatility_4h > config['volatility_exclusion']:
            return "HOLD", 35, [f"⚠️ Волатильность {volatility_4h:.1f}%"]
        
        # Volume check (более мягкий)
        avg_volume = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio < config['volume_exclusion']:
            return "HOLD", 35, [f"⚠️ Низкий объем ({volume_ratio:.0%})"]
        
        # === 1. RSI ANALYSIS (расширенные зоны) ===
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        rsi_series = 100 - (100 / (1 + rs))
        rsi = rsi_series.iloc[-1] if pd.notna(rsi_series.iloc[-1]) else 50
        rsi_prev = rsi_series.iloc[-2] if len(rsi_series) > 1 and pd.notna(rsi_series.iloc[-2]) else rsi
        rsi_trend = rsi - rsi_prev
        
        # BUY signals (расширенные зоны)
        if rsi < 30:
            buy_score += 30
            reasons.append(f"RSI {rsi:.0f} (перепродано)")
        elif rsi < config['rsi_oversold']:
            buy_score += 20
            reasons.append(f"RSI {rsi:.0f}↓")
        elif rsi < 50 and rsi_trend < 0:
            buy_score += 10
            reasons.append(f"RSI {rsi:.0f}⬇")
        elif rsi < config['rsi_buy_zone'] and rsi_trend > 0:
            buy_score += 5
            reasons.append(f"RSI {rsi:.0f}⬆")
        
        # SELL signals (расширенные зоны, лучше для медвежьего рынка)
        if rsi > 70:
            sell_score += 30
            reasons.append(f"RSI {rsi:.0f} (перекуплено)")
        elif rsi > config['rsi_overbought']:
            sell_score += 20
            reasons.append(f"RSI {rsi:.0f}↑")
        elif rsi > 50 and rsi_trend > 0:
            sell_score += 10
            reasons.append(f"RSI {rsi:.0f}⬆")
        elif rsi > config['rsi_sell_zone'] and rsi_trend < 0:
            sell_score += 5
            reasons.append(f"RSI {rsi:.0f}⬇")
        
        # === 2. MACD ANALYSIS (8-17-9) ===
        macd_line, signal_line, macd_hist = cls.calculate_macd(close, fast=8, slow=17, signal=9)
        
        # Get previous values for crossover detection
        macd_line_prev = cls.calculate_macd(close.iloc[:-1], fast=8, slow=17, signal=9)[0] if len(close) > 1 else macd_line
        signal_line_prev = cls.calculate_macd(close.iloc[:-1], fast=8, slow=17, signal=9)[1] if len(close) > 1 else signal_line
        macd_hist_prev = cls.calculate_macd(close.iloc[:-1], fast=8, slow=17, signal=9)[2] if len(close) > 1 else macd_hist
        
        # Crossover detection
        bullish_cross = macd_line_prev < signal_line_prev and macd_line > signal_line
        bearish_cross = macd_line_prev > signal_line_prev and macd_line < signal_line
        
        # Histogram momentum
        hist_growing = macd_hist > macd_hist_prev
        hist_shrinking = macd_hist < macd_hist_prev
        
        if bullish_cross:
            buy_score += 25
            reasons.append("MACD пересечение⬆")
        elif bearish_cross:
            sell_score += 25
            reasons.append("MACD пересечение⬇")
        elif macd_line > signal_line and macd_hist > 0 and hist_growing:
            buy_score += 15
            reasons.append("MACD бычий+⬆")
        elif macd_line < signal_line and macd_hist < 0 and hist_shrinking:
            sell_score += 15
            reasons.append("MACD медвежий+⬇")
        elif macd_line > signal_line:
            buy_score += 10
            if "MACD" not in str(reasons):
                reasons.append("MACD+")
        elif macd_line < signal_line:
            sell_score += 10
            if "MACD" not in str(reasons):
                reasons.append("MACD-")
        
        # === 2.5. PRE-VALIDATION: Штрафы за противоречия до финального определения ===
        # Если RSI < 35, то SELL сигналы не должны начисляться
        if rsi < 35:
            sell_score = max(0, sell_score - 50)  # Сильный штраф за SELL при перепроданности
            if sell_score > buy_score:
                reasons.append(f"⚠️ Штраф: SELL при RSI {rsi:.0f} < 35")
        
        # Если RSI > 75, то BUY сигналы не должны начисляться  
        if rsi > 75:
            buy_score = max(0, buy_score - 50)  # Сильный штраф за BUY при перекупленности
            if buy_score > sell_score:
                reasons.append(f"⚠️ Штраф: BUY при RSI {rsi:.0f} > 75")
        
        # Если MACD положительный, SELL сигналы штрафуются
        if macd_hist > 0.001:
            sell_score = max(0, sell_score - 30)
            if sell_score > buy_score and "MACD" not in str(reasons):
                reasons.append("⚠️ Штраф: SELL при MACD+")
        
        # Если MACD отрицательный, BUY сигналы штрафуются
        if macd_hist < -0.001:
            buy_score = max(0, buy_score - 30)
            if buy_score > sell_score and "MACD" not in str(reasons):
                reasons.append("⚠️ Штраф: BUY при MACD-")
        
        # === 3. PRICE CHANGE (24h) - важный фактор для медвежьего рынка ===
        if change_24h <= -5:
            sell_score += 30
            reasons.append(f"📉 Падение {change_24h:.1f}%")
        elif change_24h <= -2:
            sell_score += 20
            reasons.append(f"📉 Снижение {change_24h:.1f}%")
        elif change_24h <= -0.5:
            sell_score += 10
        elif change_24h >= 5:
            buy_score += 30
            reasons.append(f"📈 Рост {change_24h:+.1f}%")
        elif change_24h >= 2:
            buy_score += 20
            reasons.append(f"📈 Подъем {change_24h:+.1f}%")
        elif change_24h >= 0.5:
            buy_score += 10
        
        # === 4. MA TREND CONFIRMATION ===
        price = close.iloc[-1]
        ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ema20
        
        # MA alignment
        if price > ema9 > ema20 > sma50:
            buy_score += 15
            reasons.append("Тренд⬆ (EMA9>20>50)")
        elif price < ema9 < ema20 < sma50:
            sell_score += 15
            reasons.append("Тренд⬇ (EMA9<20<50)")
        elif price > ema9 > ema20:
            buy_score += 10
            reasons.append("EMA⬆")
        elif price < ema9 < ema20:
            sell_score += 10
            reasons.append("EMA⬇")
        
        # MA difference (чувствительнее)
        ma_diff_pct = (ema9 - ema20) / ema20 * 100
        if abs(ma_diff_pct) > config['ma_diff_pct'] * 100:
            if ma_diff_pct > 0:
                buy_score += 5
            else:
                sell_score += 5
        
        # === 5. VOLUME CONFIRMATION (более мягкий порог) ===
        if volume_ratio > config['volume_spike']:
            # Add bonus to the leading signal
            if buy_score > sell_score:
                buy_score += 10
                reasons.append(f"📊 Объем {volume_ratio:.1f}x")
            elif sell_score > buy_score:
                sell_score += 10
                reasons.append(f"📊 Объем {volume_ratio:.1f}x")
        
        # === 6. DIVERGENCE DETECTION (optional but valuable) ===
        # Bullish divergence: price makes lower low, but RSI makes higher low
        if len(rsi_series) >= 20:
            price_low_1 = close.tail(10).min()
            price_low_2 = close.tail(20).head(10).min()
            rsi_low_1 = rsi_series.tail(10).min()
            rsi_low_2 = rsi_series.tail(20).head(10).min()
            
            if price_low_1 < price_low_2 and rsi_low_1 > rsi_low_2:
                buy_score += 15
                reasons.append("📈 Бычья дивергенция")
            
            # Bearish divergence
            price_high_1 = close.tail(10).max()
            price_high_2 = close.tail(20).head(10).max()
            rsi_high_1 = rsi_series.tail(10).max()
            rsi_high_2 = rsi_series.tail(20).head(10).max()
            
            if price_high_1 > price_high_2 and rsi_high_1 < rsi_high_2:
                sell_score += 15
                reasons.append("📉 Медвежья дивергенция")
        
        # === 6.5. PRE-CONFIDENCE VALIDATION (определяем предварительный сигнал для проверок) ===
        diff = buy_score - sell_score
        
        # Предварительное определение сигнала для валидации
        if diff >= config['min_score_diff'] * 2:
            preliminary_signal = "BUY"
        elif diff <= -config['min_score_diff'] * 2:
            preliminary_signal = "SELL"
        elif diff >= config['min_score_diff']:
            preliminary_signal = "BUY"
        elif diff <= -config['min_score_diff']:
            preliminary_signal = "SELL"
        elif diff > 0:
            preliminary_signal = "BUY"
        elif diff < 0:
            preliminary_signal = "SELL"
        else:
            preliminary_signal = "HOLD"
        
        # === КРИТИЧЕСКИЕ ПРОВЕРКИ ПЕРЕД РАСЧЕТОМ CONFIDENCE ===
        # 1. Если SELL и price_change_24h > 10 и rsi < 55 → return SKIP (HOLD)
        if preliminary_signal == "SELL" and change_24h > 10 and rsi < 55:
            return "HOLD", 40, reasons + [f"🚫 SKIP: SELL при росте {change_24h:.1f}% и RSI {rsi:.0f} < 55"]
        
        # 2. Если SELL и rsi < 35 → return SKIP (HOLD)
        if preliminary_signal == "SELL" and rsi < 35:
            return "HOLD", 40, reasons + [f"🚫 SKIP: SELL при перепроданности RSI {rsi:.0f} < 35"]
        
        # 3. Если BUY и rsi > 75 → return SKIP (HOLD)
        if preliminary_signal == "BUY" and rsi > 75:
            return "HOLD", 40, reasons + [f"🚫 SKIP: BUY при перекупленности RSI {rsi:.0f} > 75"]
        
        # === 7. CALCULATE CONFIDENCE ===
        max_score = max(buy_score, sell_score)
        score_diff = abs(buy_score - sell_score)
        
        if max_score >= 60:
            base_confidence = 85
        elif max_score >= 45:
            base_confidence = 75
        elif max_score >= 30:
            base_confidence = 65
        elif max_score >= 20:
            base_confidence = 55
        elif max_score >= 10:
            base_confidence = 45
        else:
            base_confidence = 40
        
        # Boost confidence if score difference is significant
        if score_diff > 30:
            base_confidence = min(95, base_confidence + 10)
        elif score_diff > 20:
            base_confidence = min(90, base_confidence + 5)
        
        # === 8. DETERMINE SIGNAL (более мягкие условия) ===
        diff = buy_score - sell_score
        
        # Убрали жесткое требование RSI >= 52 для BUY
        # Теперь достаточно разницы в баллах
        if diff >= config['min_score_diff'] * 2:
            signal = "BUY"
            confidence = base_confidence
        elif diff <= -config['min_score_diff'] * 2:
            signal = "SELL"
            confidence = base_confidence
        elif diff >= config['min_score_diff']:
            signal = "BUY"
            confidence = min(base_confidence, 65)
        elif diff <= -config['min_score_diff']:
            signal = "SELL"
            confidence = min(base_confidence, 65)
        elif diff > 0:
            signal = "BUY"
            confidence = min(base_confidence, 50)
        elif diff < 0:
            signal = "SELL"
            confidence = min(base_confidence, 50)
        else:
            signal = "HOLD"
            confidence = 40
        
        # Если нет причин, добавим общую
        if not reasons:
            reasons = [f"Смешанные сигналы (BUY:{buy_score}, SELL:{sell_score})"]
        
        # === 9. ADVANCED VALIDATION (после определения сигнала, перед возвратом) ===
        validator = cls._get_validator()
        
        if validator:
            try:
                # Используем продвинутый валидатор
                symbol_str = ticker.get('symbol', 'UNKNOWN') if isinstance(ticker, dict) else str(ticker)
                
                validation_result = validator.validate(
                    symbol=symbol_str,
                    signal_direction=signal,
                    confidence=confidence,
                    rsi=rsi,
                    macd_histogram=macd_hist,
                    price_change_24h=change_24h,
                    volume_ratio=volume_ratio,
                    macd_line=macd_line,
                    signal_line=signal_line,
                    reasons=reasons
                )
                
                # Логируем детали валидации (INFO для важных, DEBUG для деталей)
                for log_entry in validation_result.validation_log:
                    if "❌" in log_entry or "🚫" in log_entry:
                        logger.warning(log_entry)
                    elif "⚠️" in log_entry or "📊" in log_entry:
                        logger.info(log_entry)
                    else:
                        logger.debug(log_entry)
                
                # Если сигнал отклонен (None) или стал HOLD
                if validation_result.signal is None:
                    rejection_reasons = ["🚫 Валидация отклонена"]
                    if validation_result.contradictions:
                        rejection_reasons.extend(validation_result.contradictions[:3])  # Ограничиваем количество
                    if validation_result.was_duplicate:
                        rejection_reasons.append("🔄 Дубликат")
                    logger.warning(f"[{symbol_str}] Signal rejected: {', '.join(rejection_reasons)}")
                    return "HOLD", 40, reasons + rejection_reasons
                
                # Добавляем информацию о валидации к причинам
                if validation_result.contradictions:
                    reasons.append(f"⚠️ Противоречия: {len(validation_result.contradictions)}")
                
                if validation_result.stats_confidence_adjustment != 0:
                    reasons.append(f"📊 Статистика: {validation_result.stats_confidence_adjustment:+.1f}%")
                
                signal = validation_result.signal
                confidence = validation_result.confidence
                
                logger.info(
                    f"[{symbol_str}] Advanced validation: {signal} "
                    f"(conf={confidence:.1f}%, contradictions={len(validation_result.contradictions)}, "
                    f"duplicate={validation_result.was_duplicate})"
                )
            except Exception as e:
                logger.error(f"Error in advanced validation: {e}", exc_info=True)
                # Fallback к старой валидации при ошибке
                validated_signal, validated_confidence = cls.critical_validation(signal, rsi, macd_hist, confidence)
                if validated_signal is None:
                    return "HOLD", 40, reasons + ["🚫 Критическая валидация: противоречие индикаторов"]
                signal = validated_signal
                confidence = validated_confidence
        else:
            # Fallback к старой валидации
            validated_signal, validated_confidence = cls.critical_validation(signal, rsi, macd_hist, confidence)
            
            if validated_signal is None:
                return "HOLD", 40, reasons + ["🚫 Критическая валидация: противоречие индикаторов"]
            
            signal = validated_signal
            confidence = validated_confidence
        
        return signal, int(confidence), reasons

