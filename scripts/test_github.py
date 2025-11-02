"""
Скрипт для тестирования того же, что и в GitHub Actions.
Помогает проверить тесты локально перед push.
"""
import sys
import subprocess
import os

def main():
    """Запускает тесты так же, как GitHub Actions."""
    print("="*60)
    print("🧪 Running tests like GitHub Actions")
    print("="*60)
    
    # Проверка зависимостей
    print("\n[1/4] Checking dependencies...")
    try:
        import pandas
        import numpy
        import pytest
        print("✅ Core dependencies OK")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return 1
    
    # Установка зависимостей
    print("\n[2/4] Installing dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q",
            "-r", "requirements-core.txt"
        ])
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q",
            "-r", "requirements-test.txt"
        ])
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("⚠️  Some dependencies may be missing")
    
    # Проверка импортов
    print("\n[3/4] Verifying imports...")
    imports_ok = True
    test_modules = [
        "indicators.smart_money.order_blocks",
        "indicators.smart_money.fair_value_gaps",
        "indicators.volume_profile.volume_profile",
        "utils.risk_manager",
    ]
    
    for module in test_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            imports_ok = False
    
    if not imports_ok:
        print("⚠️  Some imports failed, but continuing...")
    
    # Запуск тестов
    print("\n[4/4] Running tests...")
    print("="*60)
    
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=indicators",
        "--cov=utils",
        "--cov=strategies",
        "--cov-report=term-missing",
        "--maxfail=5",
        "--junit-xml=junit.xml",
        "-W", "ignore::DeprecationWarning",
    ], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("="*60)
    if result.returncode == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ Tests failed with exit code {result.returncode}")
        return result.returncode

if __name__ == "__main__":
    sys.exit(main())

