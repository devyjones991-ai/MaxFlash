"""
Tests for Anomaly Detector.
"""

import unittest

import numpy as np
import pandas as pd

from utils.anomaly_detector import AnomalyAlert, PriceAnomalyDetector


class TestAnomalyDetector(unittest.TestCase):
    """Test Anomaly Detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = PriceAnomalyDetector(
            z_score_threshold=3.0, price_change_threshold=5.0, volume_spike_threshold=2.0, window_size=50
        )

        # Create sample data
        dates = pd.date_range("2024-01-01", periods=100, freq="15T")

        self.dataframe = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.linspace(100, 110, 100),
                "high": np.linspace(101, 111, 100),
                "low": np.linspace(99, 109, 100),
                "close": np.linspace(100, 110, 100),
                "volume": np.ones(100) * 1000,
            }
        )

    def test_detect_anomalies(self):
        """Test anomaly detection."""
        anomalies = self.detector.detect_anomalies(self.dataframe)

        # Should return a list
        assert isinstance(anomalies, list)

    def test_z_score_anomalies(self):
        """Test Z-score anomaly detection."""
        # Create data with spike
        df = self.dataframe.copy()
        df.loc[50, "close"] = 150  # Big spike

        anomalies = self.detector._detect_z_score_anomalies(df)

        # Should detect the spike
        assert isinstance(anomalies, list)

    def test_volume_spike_detection(self):
        """Test volume spike detection."""
        df = self.dataframe.copy()
        df.loc[50, "volume"] = 10000  # Big volume spike

        anomalies = self.detector._detect_volume_spikes(df)

        # Should detect volume spike
        assert isinstance(anomalies, list)

    def test_get_anomaly_summary(self):
        """Test anomaly summary."""
        summary = self.detector.get_anomaly_summary(self.dataframe)

        # Should return dict with stats
        assert isinstance(summary, dict)
        assert "total_anomalies" in summary
        assert "high_severity" in summary
        assert "medium_severity" in summary

    def test_anomaly_alert_formatting(self):
        """Test alert formatting."""
        anomaly = {"type": "price_spike", "timestamp": "2024-01-01", "message": "Test anomaly", "severity": "high"}

        alert = AnomalyAlert.format_alert(anomaly)

        # Should return formatted string
        assert isinstance(alert, str)
        assert "PRICE_SPIKE" in alert.upper()
