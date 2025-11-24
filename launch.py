#!/usr/bin/env python3
"""Быстрый запуск dashboard с автоматическим открытием браузера."""

import builtins
import contextlib
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Добавляем пути
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_interface"))

os.chdir(project_root / "web_interface")


# Запускаем сервер в отдельном процессе
server_process = subprocess.Popen(
    [sys.executable, "app.py"],
    cwd=str(project_root / "web_interface"),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
)

# Ждем запуска сервера
for _i in range(15):
    time.sleep(1)
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", 8050))
        sock.close()
        if result == 0:
            break
    except:
        pass
else:
    pass

# Открываем браузер
url = "http://localhost:8050"
with contextlib.suppress(builtins.BaseException):
    webbrowser.open(url)


# Ждем завершения
try:
    server_process.wait()
except KeyboardInterrupt:
    server_process.terminate()
    server_process.wait()
