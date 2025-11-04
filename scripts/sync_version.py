"""
Скрипт для синхронизации версии между version.py и pyproject.toml.
Запускается автоматически перед коммитом или вручную.
"""
import re
import sys
from pathlib import Path

# Путь к корню проекта
PROJECT_ROOT = Path(__file__).parent.parent


def get_version_from_module():
    """Получить версию из version.py"""
    version_file = PROJECT_ROOT / "version.py"
    if not version_file.exists():
        print(f"[ERROR] Файл version.py не найден!")
        sys.exit(1)
    
    with open(version_file, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
        else:
            print("[ERROR] Не удалось найти __version__ в version.py")
            sys.exit(1)


def update_pyproject_toml(version: str):
    """Обновить версию в pyproject.toml"""
    pyproject_file = PROJECT_ROOT / "pyproject.toml"
    if not pyproject_file.exists():
        print(f"[WARNING] Файл pyproject.toml не найден")
        return False
    
    with open(pyproject_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Заменить версию в pyproject.toml
    pattern = r'version = ["\']([^"\']+)["\']'
    new_content = re.sub(pattern, f'version = "{version}"', content)
    
    if new_content != content:
        with open(pyproject_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[OK] Обновлена версия в pyproject.toml: {version}")
        return True
    else:
        print(f"[INFO] Версия в pyproject.toml уже актуальна: {version}")
        return False


def main():
    """Основная функция"""
    print("[SYNC] Синхронизация версий...")
    
    version = get_version_from_module()
    print(f"[INFO] Версия из version.py: {version}")
    
    updated = update_pyproject_toml(version)
    
    if updated:
        print(f"[OK] Синхронизация завершена!")
    else:
        print(f"[OK] Все версии синхронизированы!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

