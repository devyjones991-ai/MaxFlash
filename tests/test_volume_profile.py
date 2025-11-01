"""
Tests for Volume Profile calculator.
"""
import unittest
import pandas as pd
import numpy as np
from indicators.volume_profile.volume_profile import VolumeProfileCalculator


class TestVolumeProfile(unittest.TestCase):
    """Test Volume Profile calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = VolumeProfileCalculator(
            bins=70,
            value_area_percent=0.70
        )
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='15T')
        np.random.seed(42)
        
        self.dataframe = pd.DataFrame({
            'open': np.linspace(100, 110, 100),
            'high': np.linspace(101, 111, 100),
            'low': np.linspace(99, 109, 100),
            'close': np.linspace(100, 110, 100),
            'volume': np.random.uniform(1000, 5000, 100)
        }, index=dates)
    
    def test_calculate_volume_profile(self):
        """Test Volume Profile calculation."""
        result = self.calculator.calculate_volume_profile(self.dataframe)
        
        # Check that columns are added
        self.assertIn('vp_poc', result.columns)
        self.assertIn('vp_vah', result.columns)
        self.assertIn('vp_val', result.columns)
        self.assertIn('vp_total_volume', result.columns)
    
    def test_poc_calculation(self):
        """Test POC (Point of Control) calculation."""
        result = self.calculator.calculate_volume_profile(self.dataframe)
        
        # POC should be within price range
        price_min = self.dataframe['low'].min()
        price_max = self.dataframe['high'].max()
        
        poc = result['vp_poc'].iloc[-1]
        
        if pd.notna(poc):
            self.assertGreaterEqual(poc, price_min)
            self.assertLessEqual(poc, price_max)
    
    def test_value_area_calculation(self):
        """Test Value Area calculation."""
        result = self.calculator.calculate_volume_profile(self.dataframe)
        
        val = result['vp_val'].iloc[-1]
        vah = result['vp_vah'].iloc[-1]
        poc = result['vp_poc'].iloc[-1]
        
        if pd.notna(val) and pd.notna(vah) and pd.notna(poc):
            # VAL should be <= POC <= VAH
            self.assertLessEqual(val, poc)
            self.assertLessEqual(poc, vah)
    
    def test_hvn_lvn_detection(self):
        """Test HVN and LVN detection."""
        result = self.calculator.calculate_volume_profile(self.dataframe)
        
        summary = self.calculator.get_volume_profile_summary(result)
        
        self.assertIn('hvn', summary)
        self.assertIn('lvn', summary)
        self.assertIsInstance(summary['hvn'], list)
        self.assertIsInstance(summary['lvn'], list)
    
    def test_rolling_period(self):
        """Test Volume Profile with rolling period."""
        result = self.calculator.calculate_volume_profile(
            self.dataframe, period=20
        )
        
        # Should calculate for each period
        self.assertIn('vp_poc', result.columns)
        
        # POC should be calculated after period
        poc_values = result['vp_poc'].dropna()
        self.assertGreater(len(poc_values), 0)
    
    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        empty_df = pd.DataFrame({
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': []
        })
        
        result = self.calculator.calculate_volume_profile(empty_df)
        
        # Should handle gracefully
        self.assertIn('vp_poc', result.columns)


if __name__ == '__main__':
    unittest.main()
