#!/usr/bin/env python3
"""Быстрый запуск dashboard - минимальная версия."""
import sys
import os
from pathlib import Path

# Настройка путей
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_interface"))
os.chdir(project_root / "web_interface")

# Импорт и запуск
try:
    from app_simple import create_simple_app
    import webbrowser
    import threading
    import time

    app = create_simple_app()

    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8050")

    threading.Thread(target=open_browser, daemon=True).start()

    print("\n" + "="*60)
    print("  🚀 MAXFLASH DASHBOARD ЗАПУЩЕН")
    print("="*60)
    print("  🌐 http://localhost:8050")
    print("  ⏹️  Ctrl+C для остановки")
    print("="*60 + "\n")

    app.run_server(debug=False, host='127.0.0.1', port=8050)

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

