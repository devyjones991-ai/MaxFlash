"""
Скрипт для тестирования того же, что и в GitHub Actions.
Помогает проверить тесты локально перед push.
"""

import os
import subprocess
import sys


def main():
    """Запускает тесты так же, как GitHub Actions."""

    # Проверка зависимостей
    try:
        import numpy
        import pandas
        import pytest
    except ImportError:
        return 1

    # Установка зависимостей
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-core.txt"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-test.txt"])
    except subprocess.CalledProcessError:
        pass

    # Проверка импортов
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
        except ImportError:
            imports_ok = False

    if not imports_ok:
        pass

    # Запуск тестов

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--cov=indicators",
            "--cov=utils",
            "--cov=strategies",
            "--cov-report=term-missing",
            "--maxfail=5",
            "--junit-xml=junit.xml",
            "-W",
            "ignore::DeprecationWarning",
        ],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    if result.returncode == 0:
        return 0
    else:
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
