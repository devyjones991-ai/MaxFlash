#!/usr/bin/env python3
"""Быстрый запуск dashboard с автоматическим открытием браузера."""
import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

# Добавляем пути
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_interface"))

os.chdir(project_root / "web_interface")

print("\n" + "="*60)
print("  🚀 ЗАПУСК MAXFLASH DASHBOARD")
print("="*60)
print("\n⏳ Запускаю сервер...\n")

# Запускаем сервер в отдельном процессе
server_process = subprocess.Popen(
    [sys.executable, "app.py"],
    cwd=str(project_root / "web_interface"),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
)

# Ждем запуска сервера
print("⏳ Ожидание запуска сервера...")
for i in range(15):
    time.sleep(1)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8050))
        sock.close()
        if result == 0:
            print("✅ Сервер запущен!")
            break
    except:
        pass
    print(f"   Попытка {i+1}/15...")
else:
    print("⚠️  Сервер не ответил, но попробую открыть браузер...")

# Открываем браузер
url = "http://localhost:8050"
print(f"\n🌐 Открываю браузер: {url}\n")
try:
    webbrowser.open(url)
except:
    print(f"❌ Не удалось открыть браузер автоматически")
    print(f"   Откройте вручную: {url}\n")

print("="*60)
print("  ✅ Dashboard запущен!")
print("  🌐 URL: http://localhost:8050")
print("  ⏹️  Нажмите Ctrl+C для остановки")
print("="*60 + "\n")

# Ждем завершения
try:
    server_process.wait()
except KeyboardInterrupt:
    print("\n⏹️  Остановка сервера...")
    server_process.terminate()
    server_process.wait()
    print("✅ Сервер остановлен")

