"""
Tests for Delta analyzer.
"""
import unittest
import pandas as pd
import numpy as np
from indicators.footprint.delta import DeltaAnalyzer
from indicators.footprint.footprint_chart import FootprintChart


class TestDeltaAnalyzer(unittest.TestCase):
    """Test Delta analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.delta_analyzer = DeltaAnalyzer(delta_threshold=0.1)
        self.footprint_chart = FootprintChart()
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='15T')
        
        df = pd.DataFrame({
            'open': np.linspace(100, 110, 100),
            'high': np.linspace(101, 111, 100),
            'low': np.linspace(99, 109, 100),
            'close': np.linspace(100, 110, 100),
            'volume': np.ones(100) * 1000
        }, index=dates)
        
        # Build footprint first
        self.dataframe = self.footprint_chart.build_footprint(df)
    
    def test_calculate_delta(self):
        """Test Delta calculation."""
        result = self.delta_analyzer.calculate_delta(self.dataframe)
        
        # Check that columns are added
        self.assertIn('delta', result.columns)
        self.assertIn('delta_pct', result.columns)
        self.assertIn('delta_alignment', result.columns)
        self.assertIn('delta_divergence', result.columns)
    
    def test_delta_calculation(self):
        """Test Delta values."""
        result = self.delta_analyzer.calculate_delta(self.dataframe)
        
        # Delta should be buy_volume - sell_volume
        delta_values = result['delta'].dropna()
        self.assertGreater(len(delta_values), 0)
        
        # Check delta alignment
        alignments = result['delta_alignment'].unique()
        self.assertTrue(any(a in ['bullish', 'bearish', 'neutral'] for a in alignments))
    
    def test_divergence_detection(self):
        """Test divergence detection."""
        result = self.delta_analyzer.calculate_delta(self.dataframe)
        
        # Check divergence column exists
        self.assertIn('delta_divergence', result.columns)
    
    def test_absorption_detection(self):
        """Test absorption detection."""
        price_level = self.dataframe['close'].iloc[-1]
        
        absorption = self.delta_analyzer.detect_absorption(
            self.dataframe, price_level
        )
        
        self.assertIn('absorption_detected', absorption)
        self.assertIn('type', absorption)
        self.assertIn('strength', absorption)
        self.assertIsInstance(absorption['absorption_detected'], bool)
    
    def test_get_delta_summary(self):
        """Test Delta summary."""
        result = self.delta_analyzer.calculate_delta(self.dataframe)
        
        summary = self.delta_analyzer.get_delta_summary(result)
        
        self.assertIn('avg_delta', summary)
        self.assertIn('delta_alignment', summary)
        self.assertIn('current_delta', summary)


if __name__ == '__main__':
    unittest.main()

