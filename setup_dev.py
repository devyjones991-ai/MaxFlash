"""
Скрипт для настройки dev окружения.
"""
import subprocess
import sys
import os


def run_command(cmd: list[str]) -> bool:
    """Выполнить команду."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {' '.join(cmd)}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {' '.join(cmd)} failed:")
        print(e.stderr)
        return False


def main():
    """Основная функция установки."""
    print("="*60)
    print("🚀 MaxFlash Development Environment Setup")
    print("="*60)
    
    steps = [
        ("Upgrading pip", [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]),
        ("Installing project", [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]),
        ("Installing pre-commit", [sys.executable, "-m", "pip", "install", "pre-commit"]),
        ("Setting up pre-commit hooks", ["pre-commit", "install"]),
    ]
    
    for step_name, cmd in steps:
        print(f"\n[{step_name}]...")
        if not run_command(cmd):
            print(f"⚠️  {step_name} failed, but continuing...")
    
    print("\n" + "="*60)
    print("✅ Development environment ready!")
    print("="*60)
    print("\nДоступные команды:")
    print("  make lint      - Проверить код")
    print("  make format    - Форматировать код")
    print("  make test      - Запустить тесты")
    print("  make docker-up - Запустить Docker Compose")


if __name__ == "__main__":
    main()

