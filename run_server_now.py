#!/usr/bin/env python3
"""Запуск сервера в отдельном процессе."""
import subprocess
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.absolute()
web_interface = project_root / "web_interface"

os.chdir(str(web_interface))

# Запускаем сервер
print("\n" + "="*60)
print("  🚀 ЗАПУСК MAXFLASH DASHBOARD")
print("="*60)
print(f"\n📁 Директория: {web_interface}")
print("🌐 URL: http://localhost:8050")
print("\n⏳ Запускаю сервер...\n")

try:
    # Запускаем app_simple.py
    subprocess.run([sys.executable, "app_simple.py"], check=True)
except KeyboardInterrupt:
    print("\n\n⏹️  Сервер остановлен")
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

