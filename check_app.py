import sys
import os

sys.path.append(os.getcwd())
try:
    import web_interface.app

    print("Import success")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback

    traceback.print_exc()
