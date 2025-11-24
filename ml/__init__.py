"""ML package for MaxFlash - Machine Learning components."""

__all__ = ["LSTMSignalGenerator"]

try:
    from ml.lstm_signal_generator import LSTMSignalGenerator
except ImportError:
    LSTMSignalGenerator = None
