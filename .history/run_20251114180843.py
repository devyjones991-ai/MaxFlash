#!/usr/bin/env python3
"""
Production-ready скрипт запуска MaxFlash Trading System.
Автоматически проверяет зависимости, запускает сервер и открывает браузер.
"""

import importlib.util
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

# Попытка импорта requests для проверки сервера
try:
    import requests  # type: ignore

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    # Установим requests если нет
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests"])
        import requests  # type: ignore

        HAS_REQUESTS = True
    except (subprocess.CalledProcessError, ImportError, OSError):
        pass

# Цвета для вывода (Windows и Unix)
GREEN = "\033[92m" if sys.platform != "win32" else ""
YELLOW = "\033[93m" if sys.platform != "win32" else ""
RED = "\033[91m" if sys.platform != "win32" else ""
RESET = "\033[0m" if sys.platform != "win32" else ""


def print_status(message, status="info"):
    """Вывод статусных сообщений."""
    colors = {"info": GREEN, "warn": YELLOW, "error": RED}
    colors.get(status, "")


def check_python_version():
    """Проверка версии Python."""
    print_status(f"Python {sys.version.split()[0]} - OK", "info")


def install_dependencies():
    """Установка зависимостей."""
    print_status("Проверка зависимостей...", "info")

    required_packages = {
        "dash": "dash>=2.18.0",
        "dash_bootstrap_components": "dash-bootstrap-components>=1.6.0",
        "pandas": "pandas>=2.2.0",
        "numpy": "numpy>=1.26.0",
        "plotly": "plotly>=5.24.0",
    }

    missing = []
    for package, install_name in required_packages.items():
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(install_name)

    if missing:
        print_status(f"Установка {len(missing)} пакетов...", "warn")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", *missing])
            print_status("Зависимости установлены!", "info")
        except subprocess.CalledProcessError:
            print_status("Ошибка установки зависимостей!", "error")
            msg = "Попробуйте вручную: pip install -r requirements.txt"
            print_status(msg, "warn")
            return False
    else:
        print_status("Все зависимости установлены", "info")

    return True


def check_port(port=8050):
    """Проверка доступности порта."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(("localhost", port))
        sock.close()
        if result == 0:
            print_status(f"Порт {port} уже занят!", "warn")
            msg = "Закройте другое приложение или измените порт"
            print_status(msg, "warn")
            return False
        return True
    except OSError:
        return True


def wait_for_server(url, timeout=30):
    """Ждет пока сервер станет доступен."""
    if not HAS_REQUESTS:
        time.sleep(5)  # Fallback: просто ждем
        return True

    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)  # type: ignore
            if response.status_code == 200:
                return True
        except (requests.RequestException, OSError, ConnectionError):
            pass
        time.sleep(0.5)
    return False


def open_browser(url, delay=4):
    """Открывает браузер после задержки."""

    def _open():
        time.sleep(delay)
        if wait_for_server(url):
            print_status(f"Открываю браузер: {url}", "info")
            try:
                webbrowser.open(url)
            except (OSError, RuntimeError, webbrowser.Error) as e:
                print_status(f"Не удалось открыть браузер: {e}", "warn")
                print_status(f"Откройте вручную: {url}", "info")
        else:
            msg = "Сервер не запустился, браузер не открыт"
            print_status(msg, "warn")
            print_status(f"Откройте вручную: {url}", "info")

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def setup_paths():
    """Настройка путей для импорта."""
    project_root = Path(__file__).parent.absolute()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    web_interface = project_root / "web_interface"
    if str(web_interface) not in sys.path:
        sys.path.insert(0, str(web_interface))

    os.chdir(project_root)
    return web_interface


def run_dashboard(web_interface_path):
    """Запуск dashboard с автоматическим открытием браузера."""
    url = "http://localhost:8050"

    print_status("Запуск Dashboard...", "info")

    # Запускаем открытие браузера в фоне
    open_browser(url, delay=4)

    # Пробуем запустить приложения в порядке приоритета
    app_files = [
        web_interface_path / "app.py",  # Основное приложение
        web_interface_path / "app_modern.py",
        web_interface_path / "app_simple.py",
    ]

    for app_file in app_files:
        if app_file.exists():
            try:
                print_status(f"Запуск {app_file.name}...", "info")
                os.chdir(web_interface_path)
                # Запускаем через importlib для правильной работы
                spec = importlib.util.spec_from_file_location("__main__", app_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    # Сохраняем старый __main__
                    old_main = sys.modules.get("__main__")
                    sys.modules["__main__"] = module
                    try:
                        spec.loader.exec_module(module)
                    finally:
                        if old_main:
                            sys.modules["__main__"] = old_main
                return
            except KeyboardInterrupt:
                print_status("Остановка сервера...", "info")
                sys.exit(0)
            except (ImportError, AttributeError, OSError) as e:
                print_status(f"Ошибка в {app_file.name}: {e}", "warn")
                if "--debug" in sys.argv:
                    traceback.print_exc()
                if app_file != app_files[-1]:
                    print_status("Пробую следующую версию...", "warn")
                    continue

    print_status("Не удалось запустить dashboard!", "error")
    sys.exit(1)


def main():
    """Главная функция."""
    try:
        print_status("MaxFlash Trading System - Production Launch", "info")

        # Проверки
        check_python_version()
        if not install_dependencies():
            sys.exit(1)

        # Проверка порта
        if not check_port(8050):
            response = input("Продолжить? (y/n): ").lower()
            if response != "y":
                sys.exit(0)

        # Настройка
        web_interface_path = setup_paths()

        # Запуск
        run_dashboard(web_interface_path)

    except KeyboardInterrupt:
        print_status("Остановка...", "info")
        sys.exit(0)
    except (OSError, ImportError, AttributeError) as e:
        print_status(f"Критическая ошибка: {e}", "error")
        if "--debug" in sys.argv:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
