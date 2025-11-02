"""
Tests for Confluence calculator.
"""
import unittest
from utils.confluence import ConfluenceCalculator


class TestConfluenceCalculator(unittest.TestCase):
    """Test Confluence zone calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = ConfluenceCalculator(min_signals=3)
    
    def test_find_confluence_zones(self):
        """Test finding confluence zones."""
        order_blocks = [
            {'high': 105, 'low': 100, 'type': 'bullish'}
        ]
        
        fvgs = [
            {'high': 104, 'low': 102, 'type': 'bullish', 'strength': 1.0}
        ]
        
        volume_profile = {
            'poc': 103,
            'hvn': [102, 104],
            'lvn': []
        }
        
        market_profile = {
            'vah': 104,
            'val': 102,
            'poc': 103
        }
        
        zones = self.calculator.find_confluence_zones(
            order_blocks, fvgs, volume_profile, market_profile
        )
        
        self.assertIsInstance(zones, list)
    
    def test_is_price_in_zone(self):
        """Test price in zone check."""
        zone = {
            'high': 105,
            'low': 100,
            'level': 102.5
        }
        
        # Price in zone
        self.assertTrue(self.calculator.is_price_in_zone(102, zone))
        
        # Price below zone
        self.assertFalse(self.calculator.is_price_in_zone(99, zone))
        
        # Price above zone
        self.assertFalse(self.calculator.is_price_in_zone(106, zone))
    
    def test_min_signals_threshold(self):
        """Test minimum signals threshold."""
        calculator = ConfluenceCalculator(min_signals=5)
        
        order_blocks = [
            {'high': 105, 'low': 100, 'type': 'bullish'}
        ]
        
        fvgs = [
            {'high': 104, 'low': 102, 'type': 'bullish', 'strength': 1.0}
        ]
        
        volume_profile = {
            'poc': 103,
            'hvn': [],
            'lvn': []
        }
        
        zones = calculator.find_confluence_zones(
            order_blocks, fvgs, volume_profile
        )
        
        # With only 2 signals, should return empty if min_signals=5
        if calculator.min_signals > len(order_blocks) + len(fvgs):
            self.assertEqual(len(zones), 0)


if __name__ == '__main__':
    unittest.main()

