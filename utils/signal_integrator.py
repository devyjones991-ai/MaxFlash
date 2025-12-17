"""
Signal Integrator

Интегрирует ML предсказания с EnhancedSignalGenerator для согласованного и качественного сигнала.
Обеспечивает суммирование и улучшение качества сигналов через комбинацию rule-based и ML подходов.

Supports:
- Multi-exchange data (Binance, Bybit, OKX)
- Configurable timeframe (default: 1h for less noise)
- Consensus-based signal generation
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from utils.enhanced_signal_generator import EnhancedSignalGenerator
from ml.lightgbm_model import LightGBMSignalGenerator

# Optional imports for advanced features
try:
    from utils.advanced_signal_validator import AdvancedSignalValidator
    HAS_ADVANCED_VALIDATOR = True
except ImportError:
    HAS_ADVANCED_VALIDATOR = False

try:
    from utils.universe_selector import get_universe_selector
    HAS_UNIVERSE_SELECTOR = True
except ImportError:
    HAS_UNIVERSE_SELECTOR = False

try:
    from utils.market_data_manager import MarketDataManager
    HAS_MARKET_DATA_MANAGER = True
except ImportError:
    HAS_MARKET_DATA_MANAGER = False

logger = logging.getLogger(__name__)


class SignalIntegrator:
    """
    Интегратор сигналов: комбинирует ML и rule-based подходы для лучшего качества.
    
    Стратегия:
    1. Получает сигналы от обоих источников
    2. Анализирует согласованность
    3. Применяет весовую комбинацию с приоритетом rule-based для надежности
    4. Улучшает confidence на основе консенсуса
    5. Validates via AdvancedSignalValidator (dedupe, contradictions)
    """
    
    # Default configuration
    DEFAULT_TIMEFRAME = '1h'
    DEFAULT_EXCHANGES = ['binance', 'bybit', 'okx']
    
    def __init__(
        self,
        ml_model: Optional[LightGBMSignalGenerator] = None,
        ml_weight: float = 0.40,
        enhanced_weight: float = 0.60,
        consensus_bonus: float = 0.15,  # +15% за согласованность
        timeframe: str = '1h',
        use_validator: bool = True,
    ):
        """
        Инициализация интегратора.
        
        Args:
            ml_model: Trained LightGBM model (optional)
            ml_weight: Weight for ML predictions (default: 0.40)
            enhanced_weight: Weight for EnhancedSignalGenerator (default: 0.60)
            consensus_bonus: Bonus confidence for agreement (default: 0.15)
            timeframe: Default timeframe for analysis (default: '1h')
            use_validator: Use AdvancedSignalValidator for final check
        """
        self.ml_model = ml_model
        self.ml_weight = ml_weight
        self.enhanced_weight = enhanced_weight
        self.consensus_bonus = consensus_bonus
        self.timeframe = timeframe
        self.enhanced_generator = EnhancedSignalGenerator()
        
        # Initialize validator if available
        self.validator = None
        if use_validator and HAS_ADVANCED_VALIDATOR:
            self.validator = AdvancedSignalValidator(duplicate_window_minutes=60)  # 1h dedupe window
            logger.info("AdvancedSignalValidator initialized for signal integration")
        
        # Initialize data manager if available
        self.data_manager = None
        if HAS_MARKET_DATA_MANAGER:
            self.data_manager = MarketDataManager()
        
        # Initialize universe selector if available  
        self.universe_selector = None
        if HAS_UNIVERSE_SELECTOR:
            self.universe_selector = get_universe_selector()
        
        # Проверка весов
        if abs(ml_weight + enhanced_weight - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0, normalizing...")
            total = ml_weight + enhanced_weight
            self.ml_weight = ml_weight / total
            self.enhanced_weight = enhanced_weight / total
    
    def get_best_exchange(self, symbol: str) -> str:
        """Get best exchange for a symbol (highest volume)."""
        if self.universe_selector:
            return self.universe_selector.get_best_exchange_for_symbol(symbol)
        return 'binance'  # Default fallback
    
    def fetch_data(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        exchange_id: Optional[str] = None,
        limit: int = 100,
    ) -> Tuple[Optional[Dict], Optional[pd.DataFrame]]:
        """
        Fetch ticker and OHLCV data for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Timeframe (default: self.timeframe)
            exchange_id: Exchange to use (default: best exchange for symbol)
            limit: Number of candles
            
        Returns:
            Tuple of (ticker_dict, ohlcv_dataframe)
        """
        timeframe = timeframe or self.timeframe
        exchange_id = exchange_id or self.get_best_exchange(symbol)
        
        ticker = None
        ohlcv_df = None
        
        if self.data_manager:
            try:
                ticker = self.data_manager.get_ticker(symbol, exchange_id)
                ohlcv_df = self.data_manager.get_ohlcv(symbol, timeframe, limit, exchange_id)
            except Exception as e:
                logger.warning(f"Failed to fetch data for {symbol} from {exchange_id}: {e}")
        
        return ticker, ohlcv_df
    
    def integrate_signals(
        self,
        symbol: str,
        ticker: Optional[Dict] = None,
        ohlcv_df: Optional[pd.DataFrame] = None,
        timeframe: Optional[str] = None,
        exchange_id: Optional[str] = None,
    ) -> Dict:
        """
        Интегрирует сигналы от ML и EnhancedSignalGenerator.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            ticker: Ticker data from exchange (optional, will fetch if not provided)
            ohlcv_df: OHLCV DataFrame (optional, will fetch if not provided)
            timeframe: Timeframe for analysis (default: self.timeframe)
            exchange_id: Exchange to use (default: best for symbol)
        
        Returns:
            Integrated signal dictionary with:
            - signal: "BUY", "SELL", or "HOLD"
            - confidence: Combined confidence (0.0-1.0)
            - method: How the signal was determined
            - ml_signal: ML prediction
            - enhanced_signal: Rule-based prediction
            - reasons: List of reasons
            - exchange: Exchange used for data
            - timeframe: Timeframe used
        """
        timeframe = timeframe or self.timeframe
        exchange_id = exchange_id or self.get_best_exchange(symbol)
        
        # Fetch data if not provided
        if ticker is None or ohlcv_df is None:
            fetched_ticker, fetched_ohlcv = self.fetch_data(
                symbol, timeframe, exchange_id
            )
            ticker = ticker or fetched_ticker
            ohlcv_df = ohlcv_df if ohlcv_df is not None else fetched_ohlcv
        
        # Get EnhancedSignalGenerator signal (rule-based)
        enhanced_signal, enhanced_confidence, enhanced_reasons = self.enhanced_generator.generate_signal(
            ticker, ohlcv_df
        )
        enhanced_confidence_pct = enhanced_confidence / 100.0
        
        # Get ML signal (if model available)
        ml_signal_dict = None
        ml_confidence_pct = 0.5
        ml_action = "HOLD"
        
        if self.ml_model and ohlcv_df is not None and len(ohlcv_df) > 20:
            try:
                ml_signal_dict = self.ml_model.predict(ohlcv_df)
                ml_action = ml_signal_dict.get('action', 'HOLD')
                ml_confidence_pct = ml_signal_dict.get('confidence', 0.5)
                ml_probs = ml_signal_dict.get('probabilities', {})
                
                logger.debug(
                    f"ML prediction for {symbol}: {ml_action} "
                    f"(conf={ml_confidence_pct:.2f}, probs={ml_probs})"
                )
            except Exception as e:
                logger.warning(f"ML prediction failed for {symbol}: {e}")
                ml_signal_dict = None
        
        # Integration logic
        if ml_signal_dict is None or self.ml_model is None:
            # ML недоступен - используем только rule-based
            return {
                'signal': enhanced_signal,
                'confidence': enhanced_confidence_pct,
                'method': 'enhanced_only',
                'ml_signal': None,
                'enhanced_signal': enhanced_signal,
                'enhanced_confidence': enhanced_confidence,
                'reasons': enhanced_reasons,
                'ml_available': False,
                'symbol': symbol,
                'exchange': exchange_id,
                'timeframe': timeframe,
                'price': ticker.get('last', 0) if ticker else 0,
            }
        
        # Prepare base result fields
        base_result = {
            'symbol': symbol,
            'exchange': exchange_id,
            'timeframe': timeframe,
            'price': ticker.get('last', 0) if ticker else 0,
            'ml_available': True,
        }
        
        # Оба источника доступны - комбинируем
        ml_signal = ml_action
        ml_confidence = ml_confidence_pct
        
        if enhanced_signal == ml_action:
            # Согласованы - повышаем confidence
            combined_confidence = (
                ml_confidence_pct * self.ml_weight +
                enhanced_confidence_pct * self.enhanced_weight
            ) * (1.0 + self.consensus_bonus)
            combined_confidence = min(1.0, combined_confidence)
            consensus = True
            
            result = {
                **base_result,
                'signal': enhanced_signal,
                'confidence': combined_confidence,
                'method': 'integrated_consensus',
                'ml_signal': ml_action,
                'ml_confidence': ml_confidence_pct,
                'enhanced_signal': enhanced_signal,
                'enhanced_confidence': enhanced_confidence,
                'reasons': enhanced_reasons + [
                    f"✓ ML подтверждает: {ml_action} ({ml_confidence_pct:.0%})",
                    f"✓ Консенсус: {combined_confidence:.0%} confidence"
                ],
                'consensus': True,
            }
            return self._apply_validation(result)
        
        # Не согласованы - приоритет rule-based (более надежный)
        if enhanced_confidence > 60:  # Высокая уверенность в rule-based
            # Правило предпочтительнее
            final_signal = enhanced_signal
            final_confidence = enhanced_confidence_pct * 0.9  # Слегка снижаем
            
            result = {
                **base_result,
                'signal': final_signal,
                'confidence': final_confidence,
                'method': 'enhanced_priority',
                'ml_signal': ml_action,
                'ml_confidence': ml_confidence_pct,
                'enhanced_signal': enhanced_signal,
                'enhanced_confidence': enhanced_confidence,
                'reasons': enhanced_reasons + [
                    f"⚠️ ML предлагает {ml_action} ({ml_confidence_pct:.0%}), "
                    f"но правило предпочтительнее ({enhanced_confidence}%)"
                ],
                'consensus': False,
            }
            return self._apply_validation(result)
        
        elif ml_confidence_pct > 0.75:  # Очень высокая уверенность в ML
            # ML предпочтительнее
            final_signal = ml_action
            final_confidence = ml_confidence_pct * 0.85  # Слегка снижаем из-за несогласованности
            
            result = {
                **base_result,
                'signal': final_signal,
                'confidence': final_confidence,
                'method': 'ml_priority',
                'ml_signal': ml_action,
                'ml_confidence': ml_confidence_pct,
                'enhanced_signal': enhanced_signal,
                'enhanced_confidence': enhanced_confidence,
                'reasons': enhanced_reasons + [
                    f"⚠️ Правило предлагает {enhanced_signal} ({enhanced_confidence}%), "
                    f"но ML предпочтительнее ({ml_confidence_pct:.0%})"
                ],
                'consensus': False,
            }
            return self._apply_validation(result)
        
        else:
            # Низкая уверенность в обоих - HOLD
            return {
                **base_result,
                'signal': 'HOLD',
                'confidence': 0.5,
                'method': 'uncertain_disagreement',
                'ml_signal': ml_action,
                'ml_confidence': ml_confidence_pct,
                'enhanced_signal': enhanced_signal,
                'enhanced_confidence': enhanced_confidence,
                'reasons': enhanced_reasons + [
                    f"⚠️ Противоречие: ML={ml_action} ({ml_confidence_pct:.0%}), "
                    f"Правило={enhanced_signal} ({enhanced_confidence}%) → HOLD"
                ],
                'consensus': False,
            }
    
    def _apply_validation(self, result: Dict) -> Dict:
        """Apply AdvancedSignalValidator if available."""
        if not self.validator or result.get('signal') == 'HOLD':
            return result
        
        try:
            is_valid, validation_msg = self.validator.validate_signal({
                'symbol': result.get('symbol'),
                'signal': result.get('signal'),
                'confidence': result.get('confidence', 0) * 100,
                'reasons': result.get('reasons', []),
            })
            
            result['validated'] = is_valid
            result['validation_msg'] = validation_msg
            
            if not is_valid:
                # Downgrade to HOLD if validation fails
                result['original_signal'] = result['signal']
                result['signal'] = 'HOLD'
                result['reasons'].append(f"⛔ Validation blocked: {validation_msg}")
        except Exception as e:
            logger.warning(f"Validation error: {e}")
            result['validated'] = True  # Allow through on error
        
        return result
    
    def summarize_signal_quality(self, integrated_signal: Dict) -> Dict:
        """
        Суммирует качество интегрированного сигнала.
        
        Returns:
            Dictionary with quality metrics and summary
        """
        signal = integrated_signal.get('signal', 'HOLD')
        confidence = integrated_signal.get('confidence', 0.5)
        method = integrated_signal.get('method', 'unknown')
        consensus = integrated_signal.get('consensus', False)
        
        # Quality score (0-100)
        quality_score = confidence * 100
        
        # Метод влияет на качество
        method_multipliers = {
            'integrated_consensus': 1.0,      # Лучший - оба согласованы
            'enhanced_only': 0.95,            # Хороший - только правило
            'enhanced_priority': 0.85,        # Средний - правило предпочтительнее
            'ml_priority': 0.80,              # Средний - ML предпочтительнее
            'uncertain_disagreement': 0.50,   # Низкий - противоречие
        }
        
        quality_score *= method_multipliers.get(method, 0.75)
        
        # Consensus bonus
        if consensus:
            quality_score = min(100, quality_score + 5)
        
        # Quality categories
        if quality_score >= 75:
            quality_category = 'HIGH'
            quality_emoji = '🟢'
        elif quality_score >= 60:
            quality_category = 'MEDIUM'
            quality_emoji = '🟡'
        elif quality_score >= 45:
            quality_category = 'LOW'
            quality_emoji = '🟠'
        else:
            quality_category = 'VERY_LOW'
            quality_emoji = '🔴'
        
        return {
            'quality_score': round(quality_score, 1),
            'quality_category': quality_category,
            'quality_emoji': quality_emoji,
            'confidence': confidence,
            'method': method,
            'consensus': consensus,
            'signal': signal,
            'summary': f"{quality_emoji} {quality_category} quality ({quality_score:.1f}/100) - {signal}",
        }


