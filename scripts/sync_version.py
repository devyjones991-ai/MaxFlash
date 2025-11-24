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
        sys.exit(1)

    with open(version_file, encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
        else:
            sys.exit(1)


def update_pyproject_toml(version: str):
    """Обновить версию в pyproject.toml"""
    pyproject_file = PROJECT_ROOT / "pyproject.toml"
    if not pyproject_file.exists():
        return False

    with open(pyproject_file, encoding="utf-8") as f:
        content = f.read()

    # Заменить версию в pyproject.toml
    pattern = r'version = ["\']([^"\']+)["\']'
    new_content = re.sub(pattern, f'version = "{version}"', content)

    if new_content != content:
        with open(pyproject_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    else:
        return False


def main():
    """Основная функция"""

    version = get_version_from_module()

    updated = update_pyproject_toml(version)

    if updated:
        pass
    else:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
