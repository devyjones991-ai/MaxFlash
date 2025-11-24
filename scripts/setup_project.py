"""
Setup script for the trading system.
Installs dependencies and sets up the project structure.
"""

import os
import subprocess
import sys
from pathlib import Path


def install_requirements():
    """Install Python requirements."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError:
        return False
    return True


def install_test_requirements():
    """Install test requirements."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov", "pytest-mock"])
    except subprocess.CalledProcessError:
        return False
    return True


def create_directories():
    """Create necessary directories."""
    directories = ["data/historical", "data/backtest_results", "notebooks", "scripts", "logs"]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    return True


def check_freqtrade():
    """Check if Freqtrade is available."""
    freqtrade_path = Path("freqtrade")

    return bool(freqtrade_path.exists())


def run_tests():
    """Run tests to verify installation."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"], capture_output=True, text=True
        )

        return result.returncode == 0
    except Exception:
        return False


def main():
    """Main setup function."""

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    steps = [
        ("Creating directories", create_directories),
        ("Installing requirements", install_requirements),
        ("Installing test requirements", install_test_requirements),
        ("Checking Freqtrade", check_freqtrade),
    ]

    for _step_name, step_func in steps:
        if not step_func():
            return False

    # Ask if user wants to run tests
    response = input("\nRun tests to verify installation? (y/n): ").lower()
    if response == "y":
        run_tests()


if __name__ == "__main__":
    main()
