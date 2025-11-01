"""
Integrated Smart Money + Footprint + Volume Profile + Market Profile strategy.
Top-down multi-timeframe analysis approach.
"""
import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

try:
    from freqtrade.strategy import IStrategy, informative
    from freqtrade.strategy.informative_decorator import InformativeData
except ImportError:
    # Fallback for testing without Freqtrade installed
    class IStrategy:
        pass
    def informative(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
from strategies.base_strategy import BaseStrategy

# Import all indicators
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.smart_money.order_blocks import OrderBlockDetector
from indicators.smart_money.fair_value_gaps import FairValueGapDetector
from indicators.smart_money.market_structure import MarketStructureAnalyzer
from indicators.volume_profile.volume_profile import VolumeProfileCalculator
from indicators.market_profile.market_profile import MarketProfileCalculator
from indicators.market_profile.tpo import TPOCalculator
from indicators.footprint.footprint_chart import FootprintChart
from indicators.footprint.delta import DeltaAnalyzer
from utils.confluence import ConfluenceCalculator
from utils.risk_manager import RiskManager
from utils.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class SMCFootprintStrategy(BaseStrategy):
    """
    Integrated trading strategy combining:
    - Smart Money Concepts (Order Blocks, FVG, Market Structure)
    - Volume Profile (POC, HVN, LVN)
    - Market Profile (VAH, VAL, TPO)
    - Footprint Analysis (Delta, Order Flow)
    """
    
    # Strategy interface version
    INTERFACE_VERSION: int = 3
    
    # Timeframe for main strategy
    timeframe = '15m'
    
    # Startup candle count
    startup_candle_count: int = 500
    
    # Strategy parameters
    risk_per_trade = 0.01  # 1% risk per trade
    min_confluence_signals = 3
    
    # Order Block parameters
    ob_min_candles = 3
    ob_max_candles = 5
    ob_impulse_threshold_pct = 1.5
    
    # FVG parameters
    fvg_min_size_pct = 0.1
    fvg_max_age_bars = 50
    
    # Volume Profile parameters
    vp_period = 20
    vp_value_area_percent = 0.70
    
    # Market Profile parameters
    mp_period = 24
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        
        # Initialize detectors
        self.ob_detector = OrderBlockDetector(
            min_candles=self.ob_min_candles,
            max_candles=self.ob_max_candles,
            impulse_threshold_pct=self.ob_impulse_threshold_pct
        )
        
        self.fvg_detector = FairValueGapDetector(
            min_size_pct=self.fvg_min_size_pct,
            max_age_bars=self.fvg_max_age_bars
        )
        
        self.market_structure = MarketStructureAnalyzer()
        
        self.vp_calculator = VolumeProfileCalculator(
            value_area_percent=self.vp_value_area_percent
        )
        
        self.mp_calculator = MarketProfileCalculator(
            period=self.mp_period
        )
        
        self.tpo_calculator = TPOCalculator()
        
        self.footprint_chart = FootprintChart()
        self.delta_analyzer = DeltaAnalyzer()
        
        self.confluence_calc = ConfluenceCalculator(
            min_signals=self.min_confluence_signals
        )
        
        self.risk_manager = RiskManager(
            risk_per_trade=self.risk_per_trade
        )
        
        self.data_fetcher = DataFetcher()
        
        # Store multi-timeframe data
        self.macro_data = None
        self.intermediate_data = None
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Add indicators to the dataframe.
        """
        # Calculate ATR
        dataframe['atr'] = self.calculate_atr(dataframe, period=14)
        
        # Footprint and Delta analysis (micro level)
        dataframe = self.footprint_chart.build_footprint(dataframe)
        dataframe = self.delta_analyzer.calculate_delta(dataframe)
        
        # Smart Money Concepts
        dataframe = self.ob_detector.detect_order_blocks(dataframe)
        dataframe = self.fvg_detector.detect_fair_value_gaps(dataframe)
        dataframe = self.market_structure.analyze_market_structure(dataframe)
        
        # Volume Profile
        dataframe = self.vp_calculator.calculate_volume_profile(
            dataframe, period=self.vp_period
        )
        
        # Market Profile
        dataframe = self.mp_calculator.calculate_market_profile(dataframe)
        dataframe = self.tpo_calculator.calculate_tpo_distribution(dataframe)
        
        return dataframe
    
    @informative('1h', '1h_{base}')
    def populate_indicators_1h(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Populate indicators for 1-hour timeframe (intermediate level).
        """
        # Market Profile for intermediate level
        dataframe = self.mp_calculator.calculate_market_profile(dataframe)
        dataframe = self.tpo_calculator.calculate_tpo_distribution(dataframe)
        
        # Volume Profile
        dataframe = self.vp_calculator.calculate_volume_profile(
            dataframe, period=self.vp_period
        )
        
        return dataframe
    
    @informative('1d', '1d_{base}')
    def populate_indicators_1d(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Populate indicators for daily timeframe (macro level).
        """
        # Smart Money Concepts for macro
        dataframe = self.ob_detector.detect_order_blocks(dataframe)
        dataframe = self.fvg_detector.detect_fair_value_gaps(dataframe)
        dataframe = self.market_structure.analyze_market_structure(dataframe)
        
        # Volume Profile
        dataframe = self.vp_calculator.calculate_volume_profile(
            dataframe, period=50  # Longer period for daily
        )
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entry logic based on top-down analysis.
        """
        # Get multi-timeframe data
        macro_df = dataframe[[col for col in dataframe.columns if col.startswith('1d_')]]
        intermediate_df = dataframe[[col for col in dataframe.columns if col.startswith('1h_')]]
        
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        
        for i in range(self.startup_candle_count, len(dataframe)):
            # Analyze macro level
            macro_analysis = self._analyze_macro_level(
                dataframe.iloc[i], macro_df.iloc[i] if len(macro_df) > i else None
            )
            
            # Analyze intermediate level
            intermediate_analysis = self._analyze_intermediate_level(
                dataframe.iloc[i], intermediate_df.iloc[i] if len(intermediate_df) > i else None
            )
            
            # Analyze micro level
            micro_analysis = self._analyze_micro_level(dataframe.iloc[i])
            
            # Check confluence
            confluence_score = self._calculate_confluence(
                macro_analysis, intermediate_analysis, micro_analysis
            )
            
            # Entry conditions
            if confluence_score >= self.min_confluence_signals:
                # Long entry
                if (macro_analysis.get('trend') in ['bullish', 'range'] and
                    macro_analysis.get('in_order_block') and
                    macro_analysis.get('order_block_type') == 'bullish' and
                    intermediate_analysis.get('in_value_area', True) and
                    micro_analysis.get('delta_alignment') == 'bullish' and
                    micro_analysis.get('absorption_detected', False)):
                    
                    dataframe.loc[dataframe.index[i], 'enter_long'] = 1
                
                # Short entry
                elif (macro_analysis.get('trend') in ['bearish', 'range'] and
                      macro_analysis.get('in_order_block') and
                      macro_analysis.get('order_block_type') == 'bearish' and
                      intermediate_analysis.get('in_value_area', True) and
                      micro_analysis.get('delta_alignment') == 'bearish' and
                      micro_analysis.get('absorption_detected', False)):
                    
                    dataframe.loc[dataframe.index[i], 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Exit logic based on targets and stop loss.
        """
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Custom stop loss based on Order Blocks.
        """
        # Get current dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return self.stoploss
        
        current_data = dataframe.iloc[-1]
        
        # Use Order Block levels for stop loss
        if trade.is_long:
            if pd.notna(current_data.get('ob_bullish_low')):
                stop_loss = current_data['ob_bullish_low'] * 0.999
                return (stop_loss - current_rate) / current_rate
        else:
            if pd.notna(current_data.get('ob_bearish_high')):
                stop_loss = current_data['ob_bearish_high'] * 1.001
                return (stop_loss - current_rate) / current_rate
        
        return self.stoploss
    
    def _analyze_macro_level(
        self,
        current_data: pd.Series,
        macro_data: Optional[pd.Series]
    ) -> Dict:
        """Analyze macro level (Daily/4H)."""
        if macro_data is None:
            return {}
        
        analysis = {
            'trend': macro_data.get('market_structure', 'range'),
            'in_order_block': False,
            'order_block_type': None,
            'in_fvg': False,
            'fvg_type': None,
            'poc': macro_data.get('vp_poc'),
            'hvn': [],
        }
        
        # Check Order Block
        current_price = current_data['close']
        
        if pd.notna(macro_data.get('ob_bullish_low')):
            if (macro_data['ob_bullish_low'] <= current_price <=
                macro_data['ob_bullish_high']):
                analysis['in_order_block'] = True
                analysis['order_block_type'] = 'bullish'
        
        if pd.notna(macro_data.get('ob_bearish_low')):
            if (macro_data['ob_bearish_low'] <= current_price <=
                macro_data['ob_bearish_high']):
                analysis['in_order_block'] = True
                analysis['order_block_type'] = 'bearish'
        
        # Check FVG
        if pd.notna(macro_data.get('fvg_bullish_low')):
            if (macro_data['fvg_bullish_low'] <= current_price <=
                macro_data['fvg_bullish_high']):
                analysis['in_fvg'] = True
                analysis['fvg_type'] = 'bullish'
        
        return analysis
    
    def _analyze_intermediate_level(
        self,
        current_data: pd.Series,
        intermediate_data: Optional[pd.Series]
    ) -> Dict:
        """Analyze intermediate level (1H)."""
        if intermediate_data is None:
            return {'in_value_area': True}  # Default to allow trading
        
        current_price = current_data['close']
        
        analysis = {
            'vah': intermediate_data.get('mp_vah'),
            'val': intermediate_data.get('mp_val'),
            'poc': intermediate_data.get('mp_poc'),
            'market_state': intermediate_data.get('mp_market_state', 'balanced'),
        }
        
        # Check if price is in Value Area
        val = intermediate_data.get('mp_val')
        vah = intermediate_data.get('mp_vah')
        
        if pd.notna(val) and pd.notna(vah):
            analysis['in_value_area'] = val <= current_price <= vah
        else:
            analysis['in_value_area'] = True
        
        return analysis
    
    def _analyze_micro_level(self, current_data: pd.Series) -> Dict:
        """Analyze micro level (5-15min)."""
        analysis = {
            'delta_alignment': current_data.get('delta_alignment', 'neutral'),
            'delta_value': current_data.get('delta', 0),
            'absorption_detected': False,
        }
        
        # Check for absorption at current price
        current_price = current_data['close']
        absorption = self.delta_analyzer.detect_absorption(
            pd.DataFrame([current_data]),  # Single row dataframe
            current_price
        )
        
        analysis['absorption_detected'] = absorption['absorption_detected']
        
        return analysis
    
    def _calculate_confluence(
        self,
        macro: Dict,
        intermediate: Dict,
        micro: Dict
    ) -> int:
        """Calculate confluence score."""
        score = 0
        
        # Macro signals
        if macro.get('in_order_block'):
            score += 1
        if macro.get('in_fvg'):
            score += 1
        if macro.get('trend') in ['bullish', 'bearish']:
            score += 1
        
        # Intermediate signals
        if intermediate.get('in_value_area'):
            score += 1
        if intermediate.get('market_state') == 'balanced':
            score += 1
        
        # Micro signals
        if micro.get('delta_alignment') != 'neutral':
            score += 1
        if micro.get('absorption_detected'):
            score += 1
        
        return score
    
    # Minimal ROI table
    minimal_roi = {
        "0": 0.10,  # 10% after entry
        "60": 0.05,  # 5% after 60 minutes
        "120": 0.03,  # 3% after 2 hours
        "240": 0.01,  # 1% after 4 hours
    }
    
    # Stop loss
    stoploss = -0.10  # 10% stop loss
    
    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
