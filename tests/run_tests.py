"""
Test runner script.
Run all tests with: python tests/run_tests.py
"""
import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Discover and add all test files
    test_files = [
        'tests.test_order_blocks',
        'tests.test_fair_value_gaps',
        'tests.test_volume_profile',
        'tests.test_market_profile',
        'tests.test_delta',
        'tests.test_confluence',
        'tests.test_risk_manager',
        'tests.test_market_structure',
    ]
    
    for test_file in test_files:
        try:
            tests = loader.loadTestsFromName(test_file)
            suite.addTests(tests)
        except ImportError as e:
            print(f"Warning: Could not import {test_file}: {e}")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
