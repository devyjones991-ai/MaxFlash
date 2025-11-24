import sys
import os
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Sys path: {sys.path}")

try:
    print("Attempting to import ml.lstm_signal_generator...")
    from ml.lstm_signal_generator import LSTMSignalGenerator

    print("✅ Imported LSTMSignalGenerator successfully")
except Exception:
    print("❌ Failed to import LSTMSignalGenerator")
    traceback.print_exc()

try:
    print("Attempting to import api.main...")
    from api.main import app

    print("✅ Imported api.main successfully")
except Exception:
    print("❌ Failed to import api.main")
    traceback.print_exc()
