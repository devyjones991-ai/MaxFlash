"""
Value Area calculation module (70% of volume).
This is already included in volume_profile.py, but kept as separate module for compatibility.
"""
try:
    from indicators.volume_profile.volume_profile import VolumeProfileCalculator
except ImportError:
    # For relative imports
    from .volume_profile import VolumeProfileCalculator

# Re-export for convenience
__all__ = ['VolumeProfileCalculator']
