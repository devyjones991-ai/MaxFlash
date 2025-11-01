"""
Tests for Market Profile calculator.
"""
import unittest
import pandas as pd
import numpy as np
from indicators.market_profile.market_profile import MarketProfileCalculator


class TestMarketProfile(unittest.TestCase):
    """Test Market Profile calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = MarketProfileCalculator(
            bins=30,
            value_area_percent=0.70,
            period=24
        )
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='15T')
        
        self.dataframe = pd.DataFrame({
            'open': np.linspace(100, 110, 100),
            'high': np.linspace(101, 111, 100),
            'low': np.linspace(99, 109, 100),
            'close': np.linspace(100, 110, 100),
            'volume': np.ones(100) * 1000
        }, index=dates)
    
    def test_calculate_market_profile(self):
        """Test Market Profile calculation."""
        result = self.calculator.calculate_market_profile(self.dataframe)
        
        # Check that columns are added
        self.assertIn('mp_poc', result.columns)
        self.assertIn('mp_vah', result.columns)
        self.assertIn('mp_val', result.columns)
        self.assertIn('mp_market_state', result.columns)
    
    def test_value_area_calculation(self):
        """Test Value Area High/Low calculation."""
        result = self.calculator.calculate_market_profile(self.dataframe)
        
        val = result['mp_val'].iloc[-1]
        vah = result['mp_vah'].iloc[-1]
        poc = result['mp_poc'].iloc[-1]
        
        if pd.notna(val) and pd.notna(vah) and pd.notna(poc):
            # VAL <= POC <= VAH
            self.assertLessEqual(val, poc)
            self.assertLessEqual(poc, vah)
    
    def test_market_state_determination(self):
        """Test market state (trending vs balanced) determination."""
        result = self.calculator.calculate_market_profile(self.dataframe)
        
        market_state = result['mp_market_state'].iloc[-1]
        
        self.assertIn(market_state, ['trending', 'balanced', None])
    
    def test_profile_high_low(self):
        """Test profile high and low calculation."""
        result = self.calculator.calculate_market_profile(self.dataframe)
        
        profile_high = result['mp_profile_high'].iloc[-1]
        profile_low = result['mp_profile_low'].iloc[-1]
        
        if pd.notna(profile_high) and pd.notna(profile_low):
            self.assertGreaterEqual(profile_high, profile_low)
    
    def test_rolling_period(self):
        """Test Market Profile with rolling period."""
        result = self.calculator.calculate_market_profile(self.dataframe)
        
        # Should calculate for each period after initial period
        poc_values = result['mp_poc'].dropna()
        self.assertGreater(len(poc_values), 0)


if __name__ == '__main__':
    unittest.main()
