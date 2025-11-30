import sys
import os

# Add project root to path (simulating dashboard.py behavior)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

print(f"Current Dir: {current_dir}")
print(f"Sys Path: {sys.path}")


def debug_imports():
    print("\n--- Listing Directory Structure ---")
    print(f"Contents of {current_dir}:")
    print(os.listdir(current_dir))

    app_dir = os.path.join(current_dir, "app")
    if os.path.exists(app_dir):
        print(f"\nContents of {app_dir}:")
        print(os.listdir(app_dir))
    else:
        print(f"\n{app_dir} does not exist!")

    print("\n--- Testing Imports ---")
    try:
        import app

        print(f"Successfully imported 'app'. File: {getattr(app, '__file__', 'unknown')}")
        print(f"Is package? {hasattr(app, '__path__')}")
    except ImportError as e:
        print(f"Failed to import 'app': {e}")

    try:
        import app.config

        print(f"Successfully imported 'app.config'. File: {getattr(app.config, '__file__', 'unknown')}")
    except ImportError as e:
        print(f"Failed to import 'app.config': {e}")
    except Exception as e:
        print(f"Error importing 'app.config': {e}")


if __name__ == "__main__":
    debug_imports()
