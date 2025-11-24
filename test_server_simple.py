#!/usr/bin/env python3
"""Простой тест запуска сервера."""

import os
import sys
from pathlib import Path

# Настройка путей
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_interface"))
os.chdir(project_root / "web_interface")


try:
    from app_simple import create_simple_app

    app = create_simple_app()

    # Запускаем сервер
    app.run_server(debug=False, host="127.0.0.1", port=8050, use_reloader=False)

except KeyboardInterrupt:
    pass
except Exception:
    import traceback

    traceback.print_exc()
    sys.exit(1)
