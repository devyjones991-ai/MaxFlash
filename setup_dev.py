"""
Скрипт для настройки dev окружения.
"""

import subprocess
import sys


def run_command(cmd: list[str]) -> bool:
    """Выполнить команду."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            pass
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Основная функция установки."""

    steps = [
        ("Upgrading pip", [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]),
        ("Installing project", [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]),
        ("Installing pre-commit", [sys.executable, "-m", "pip", "install", "pre-commit"]),
        ("Setting up pre-commit hooks", ["pre-commit", "install"]),
    ]

    for _step_name, cmd in steps:
        if not run_command(cmd):
            pass


if __name__ == "__main__":
    main()
