#!/usr/bin/env python3
"""Запуск сервера в отдельном процессе."""

import os
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.absolute()
web_interface = project_root / "web_interface"

os.chdir(str(web_interface))

# Запускаем сервер

try:
    # Запускаем app_simple.py
    subprocess.run([sys.executable, "app_simple.py"], check=True)
except KeyboardInterrupt:
    pass
except Exception:
    import traceback

    traceback.print_exc()
