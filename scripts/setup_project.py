"""
Setup script for the trading system.
Installs dependencies and sets up the project structure.
"""
import os
import sys
import subprocess
from pathlib import Path


def install_requirements():
    """Install Python requirements."""
    print("Installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False
    return True


def install_test_requirements():
    """Install test requirements."""
    print("\nInstalling test requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov", "pytest-mock"])
        print("✅ Test requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing test requirements: {e}")
        return False
    return True


def create_directories():
    """Create necessary directories."""
    print("\nCreating project directories...")
    directories = [
        "data/historical",
        "data/backtest_results",
        "notebooks",
        "scripts",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✓ Created {directory}")
    
    return True


def check_freqtrade():
    """Check if Freqtrade is available."""
    print("\nChecking Freqtrade setup...")
    freqtrade_path = Path("freqtrade")
    
    if freqtrade_path.exists():
        print("✅ Freqtrade directory found")
        return True
    else:
        print("⚠️  Freqtrade directory not found")
        print("   Please run: git clone https://github.com/freqtrade/freqtrade.git")
        return False


def run_tests():
    """Run tests to verify installation."""
    print("\nRunning tests...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("⚠️  Some tests failed:")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"⚠️  Could not run tests: {e}")
        return False


def main():
    """Main setup function."""
    print("="*60)
    print("Trading System Setup")
    print("="*60)
    
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
    
    for step_name, step_func in steps:
        if not step_func():
            print(f"\n❌ Setup failed at: {step_name}")
            return False
    
    # Ask if user wants to run tests
    response = input("\nRun tests to verify installation? (y/n): ").lower()
    if response == 'y':
        run_tests()
    
    print("\n" + "="*60)
    print("✅ Setup completed successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Configure your exchange API in config/config.json")
    print("2. Customize strategy parameters in config/strategy_params.json")
    print("3. Run backtesting: cd freqtrade && freqtrade backtesting --strategy SMCFootprintStrategy")
    print("\n")


if __name__ == "__main__":
    main()
