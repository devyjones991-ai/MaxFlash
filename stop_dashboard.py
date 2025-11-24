#!/usr/bin/env python3
"""
Остановка фонового процесса dashboard.
"""

import builtins
import contextlib
import os
import signal
from pathlib import Path


def stop_windows():
    """Остановка на Windows."""
    import subprocess

    # Ищем процессы python/pythonw с app_simple.py
    try:
        subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"], capture_output=True, text=True)

        # Также проверяем pythonw.exe
        subprocess.run(["tasklist", "/FI", "IMAGENAME eq pythonw.exe", "/FO", "CSV"], capture_output=True, text=True)

        # Простой способ - убиваем все процессы на порту 8050
        try:
            subprocess.run(["netstat", "-ano"], capture_output=True)
            # Используем PowerShell для поиска и убийства процесса на порту
            ps_cmd = """
            $port = 8050
            $process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $process.OwningProcess -Force
                Write-Host "Процесс остановлен"
            } else {
                Write-Host "Процесс не найден"
            }
            """
            subprocess.run(["powershell", "-Command", ps_cmd])
        except:
            pass

    except Exception:
        pass


def stop_linux():
    """Остановка на Linux/Mac."""
    pid_file = Path(__file__).parent / "dashboard.pid"

    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            pid_file.unlink()
        except ProcessLookupError:
            pid_file.unlink()
        except Exception:
            pass
    else:
        # Ищем процесс по имени
        import subprocess

        try:
            result = subprocess.run(["pgrep", "-f", "app_simple.py"], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    with contextlib.suppress(builtins.BaseException):
                        os.kill(int(pid), signal.SIGTERM)
            else:
                pass
        except:
            pass


def main():
    """Главная функция."""
    import platform

    system = platform.system()

    if system == "Windows":
        stop_windows()
    else:
        stop_linux()


if __name__ == "__main__":
    main()
