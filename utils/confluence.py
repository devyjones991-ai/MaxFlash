"""
Confluence zone calculator.
Combines signals from multiple sources to identify high-probability trading zones.
"""
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np


class ConfluenceCalculator:
    """
    Calculates confluence zones from multiple trading signals.
    """
    
    def __init__(self, min_signals: int = 3):
        """
        Initialize confluence calculator.
        
        Args:
            min_signals: Minimum number of signals required for confluence
        """
        self.min_signals = min_signals
    
    def find_confluence_zones(
        self,
        order_blocks: List[Dict],
        fvgs: List[Dict],
        volume_profile: Dict,
        market_profile: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Find confluence zones from multiple signal sources.
        
        Args:
            order_blocks: List of order block dictionaries with 'high', 'low', 'type'
            fvgs: List of FVG dictionaries with 'high', 'low', 'strength'
            volume_profile: Dictionary with 'poc', 'hvn', 'lvn' levels
            market_profile: Optional dictionary with 'vah', 'val', 'poc'
            
        Returns:
            List of confluence zones with strength scores
        """
        zones = []
        
        # Collect all price levels
        all_levels = []
        
        # Add order block levels
        for ob in order_blocks:
            all_levels.append({
                'type': 'order_block',
                'level': (ob['high'] + ob['low']) / 2,
                'high': ob['high'],
                'low': ob['low'],
                'strength': 1.0
            })
        
        # Add FVG levels
        for fvg in fvgs:
            all_levels.append({
                'type': 'fvg',
                'level': (fvg['high'] + fvg['low']) / 2,
                'high': fvg['high'],
                'low': fvg['low'],
                'strength': fvg.get('strength', 1.0)
            })
        
        # Add volume profile levels
        if volume_profile:
            if 'poc' in volume_profile:
                all_levels.append({
                    'type': 'vp_poc',
                    'level': volume_profile['poc'],
                    'high': volume_profile['poc'],
                    'low': volume_profile['poc'],
                    'strength': 2.0  # POC is stronger
                })
            
            for hvn in volume_profile.get('hvn', []):
                all_levels.append({
                    'type': 'vp_hvn',
                    'level': hvn,
                    'high': hvn,
                    'low': hvn,
                    'strength': 1.5
                })
        
        # Add market profile levels
        if market_profile:
            for level_key in ['vah', 'val', 'poc']:
                if level_key in market_profile:
                    all_levels.append({
                        'type': f'mp_{level_key}',
                        'level': market_profile[level_key],
                        'high': market_profile[level_key],
                        'low': market_profile[level_key],
                        'strength': 1.5 if level_key == 'poc' else 1.0
                    })
        
        # Filter out None levels
        all_levels = [l for l in all_levels if l.get('level') is not None and pd.notna(l.get('level'))]
        
        if not all_levels:
            return zones
        
        # Group nearby levels (within 0.5% of price)
        grouped_zones = self._group_nearby_levels(all_levels)
        
        # Calculate confluence strength
        for zone in grouped_zones:
            if zone['signal_count'] >= self.min_signals:
                zones.append({
                    'level': zone['level'],
                    'high': zone['high'],
                    'low': zone['low'],
                    'strength': zone['total_strength'],
                    'signals': zone['signals'],
                    'signal_count': zone['signal_count']
                })
        
        # Sort by strength
        zones.sort(key=lambda x: x['strength'], reverse=True)
        
        return zones
    
    def _group_nearby_levels(
        self,
        levels: List[Dict],
        tolerance_pct: float = 0.005
    ) -> List[Dict]:
        """
        Group price levels that are close to each other.
        
        Args:
            levels: List of level dictionaries
            tolerance_pct: Percentage tolerance for grouping (default 0.5%)
            
        Returns:
            List of grouped zones
        """
        if not levels:
            return []
        
        # Sort by price level, filtering out None levels
        valid_levels = [l for l in levels if l['level'] is not None and pd.notna(l['level'])]
        sorted_levels = sorted(valid_levels, key=lambda x: x['level'])
        
        grouped = []
        current_group = {
            'levels': [],
            'signals': [],
            'total_strength': 0.0
        }
        
        for level in sorted_levels:
            if not current_group['levels']:
                current_group['levels'].append(level)
                current_group['signals'].append(level['type'])
                current_group['total_strength'] += level['strength']
            else:
                # Check if level is within tolerance
                last_level = current_group['levels'][-1]
                tolerance = last_level['level'] * tolerance_pct
                
                if abs(level['level'] - last_level['level']) <= tolerance:
                    # Add to current group
                    current_group['levels'].append(level)
                    current_group['signals'].append(level['type'])
                    current_group['total_strength'] += level['strength']
                else:
                    # Save current group and start new one
                    if current_group['levels']:
                        grouped.append(self._create_zone_from_group(current_group))
                    current_group = {
                        'levels': [level],
                        'signals': [level['type']],
                        'total_strength': level['strength']
                    }
        
        # Add last group
        if current_group['levels']:
            grouped.append(self._create_zone_from_group(current_group))
        
        return grouped
    
    def _create_zone_from_group(self, group: Dict) -> Dict:
        """
        Create a confluence zone from a group of levels.
        
        Args:
            group: Group dictionary with levels
            
        Returns:
            Zone dictionary
        """
        levels = group['levels']
        
        # Calculate zone boundaries
        highs = [l['high'] for l in levels]
        lows = [l['low'] for l in levels]
        prices = [l['level'] for l in levels]
        
        return {
            'level': np.mean(prices),
            'high': max(highs),
            'low': min(lows),
            'signals': list(set(group['signals'])),
            'signal_count': len(set(group['signals'])),
            'total_strength': group['total_strength']
        }
    
    def is_price_in_zone(
        self,
        price: float,
        zone: Dict,
        tolerance_pct: float = 0.002
    ) -> bool:
        """
        Check if price is within a confluence zone.
        
        Args:
            price: Current price
            zone: Zone dictionary with 'high' and 'low'
            tolerance_pct: Percentage tolerance
            
        Returns:
            True if price is in zone
        """
        tolerance = price * tolerance_pct
        return zone['low'] - tolerance <= price <= zone['high'] + tolerance
