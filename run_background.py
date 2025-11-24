#!/usr/bin/env python3
"""
Production-ready скрипт для запуска MaxFlash Dashboard в фоне.
Поддерживает Windows и Linux/Mac.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def run_windows_background():
    """Запуск в фоне на Windows."""
    project_root = Path(__file__).parent.absolute()
    web_interface = project_root / "web_interface"
    web_interface / "app_simple.py"

    # Используем pythonw.exe для запуска без консоли
    python_exe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    # Создаем лог файл
    log_file = project_root / "dashboard.log"

    # Создаем VBS скрипт для скрытого запуска
    vbs_script = project_root / "start_hidden.vbs"
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set logFile = fso.OpenTextFile("{log_file}", 2, True)
logFile.WriteLine "MaxFlash Dashboard started at " & Now()
logFile.Close

WshShell.Run "cmd /c cd /d {web_interface} && {python_exe} app_simple.py >> {log_file} 2>&1", 0, False
Set WshShell = Nothing
Set fso = Nothing
'''
    vbs_script.write_text(vbs_content, encoding="utf-8")

    # Запускаем через VBS (скрыто)
    subprocess.Popen(
        ["wscript.exe", str(vbs_script)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return True


def run_linux_background():
    """Запуск в фоне на Linux/Mac."""
    project_root = Path(__file__).parent.absolute()
    web_interface = project_root / "web_interface"
    script_path = web_interface / "app_simple.py"

    # Используем nohup для запуска в фоне
    log_file = project_root / "dashboard.log"

    with open(log_file, "w") as log:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(web_interface),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # Отдельная сессия
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

    # Сохраняем PID
    pid_file = project_root / "dashboard.pid"
    pid_file.write_text(str(process.pid))

    return True


def run_foreground():
    """Запуск в обычном режиме (для отладки)."""
    project_root = Path(__file__).parent.absolute()
    web_interface = project_root / "web_interface"
    web_interface / "app_simple.py"

    os.chdir(str(web_interface))
    subprocess.run([sys.executable, "app_simple.py"])


def main():
    """Главная функция."""
    if len(sys.argv) > 1 and sys.argv[1] == "--foreground":
        run_foreground()
        return

    system = platform.system()

    if system == "Windows":
        run_windows_background()
    elif system in ["Linux", "Darwin"]:  # Darwin = Mac
        run_linux_background()
    else:
        run_foreground()


if __name__ == "__main__":
    main()
