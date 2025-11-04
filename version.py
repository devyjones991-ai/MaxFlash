"""
Централизованное управление версиями MaxFlash Trading System.

Этот модуль содержит единственный источник истины для версии проекта.
Все остальные модули должны импортировать версию отсюда.
"""

# Версия проекта (Semantic Versioning: MAJOR.MINOR.PATCH)
__version__ = "1.0.0"

# Компоненты версии
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0

# Метаданные версии
VERSION_BUILD = None  # Для CI/CD можно добавить номер сборки
VERSION_COMMIT = None  # Git commit hash


def get_version() -> str:
    """
    Получить полную версию проекта.

    Returns:
        Строка версии в формате MAJOR.MINOR.PATCH
    """
    return __version__


def get_version_tuple() -> tuple[int, int, int]:
    """
    Получить версию в виде кортежа.

    Returns:
        Кортеж (MAJOR, MINOR, PATCH)
    """
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


def get_version_info() -> dict:
    """
    Получить полную информацию о версии.

    Returns:
        Словарь с информацией о версии
    """
    info = {
        "version": __version__,
        "major": VERSION_MAJOR,
        "minor": VERSION_MINOR,
        "patch": VERSION_PATCH,
    }

    if VERSION_BUILD:
        info["build"] = VERSION_BUILD
    if VERSION_COMMIT:
        info["commit"] = VERSION_COMMIT

    return info


def increment_version(
    major: bool = False, minor: bool = False, patch: bool = True
) -> str:
    """
    Инкрементировать версию (для использования в скриптах).

    Args:
        major: Инкрементировать major версию
        minor: Инкрементировать minor версию
        patch: Инкрементировать patch версию (по умолчанию)

    Returns:
        Новая версия в виде строки
    """
    # Эта функция используется только для генерации новой версии
    # Реальная версия должна обновляться вручную или через CI/CD
    new_major = VERSION_MAJOR + 1 if major else VERSION_MAJOR
    new_minor = (
        VERSION_MINOR + 1 if minor else (0 if major else VERSION_MINOR)
    )
    new_patch = (
        VERSION_PATCH + 1
        if patch and not (major or minor)
        else (0 if (major or minor) else VERSION_PATCH)
    )

    return f"{new_major}.{new_minor}.{new_patch}"


if __name__ == "__main__":
    # Вывод версии для использования в скриптах
    print(get_version())

