#!/usr/bin/env python3
"""Простой тест запуска сервера."""
import sys
import os
from pathlib import Path

# Настройка путей
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_interface"))
os.chdir(project_root / "web_interface")

print("\n" + "="*60)
print("  ТЕСТ ЗАПУСКА MAXFLASH DASHBOARD")
print("="*60)
print()

try:
    from app_simple import create_simple_app
    print("[OK] Импорт app_simple успешен")
    
    app = create_simple_app()
    print("[OK] Приложение создано")
    
    print("\n" + "="*60)
    print("  СЕРВЕР ЗАПУСКАЕТСЯ...")
    print("="*60)
    print("  URL: http://localhost:8050")
    print("  Нажмите Ctrl+C для остановки")
    print("="*60 + "\n")
    
    # Запускаем сервер
    app.run_server(
        debug=False,
        host='127.0.0.1',
        port=8050,
        use_reloader=False
    )
    
except KeyboardInterrupt:
    print("\n\n[INFO] Сервер остановлен пользователем")
except Exception as e:
    print(f"\n[ERROR] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

