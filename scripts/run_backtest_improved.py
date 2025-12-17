#!/usr/bin/env python3
"""
Запуск улучшенного бэктеста с фильтрацией по confidence.
"""

import paramiko
import sys
import time

SERVER = "192.168.0.203"
PORT = 22
USER = "devyjones"
PASSWORD = "19Maxon91!"
REMOTE_PATH = "/home/devyjones/MaxFlash"


def execute_remote_command(ssh, command, description):
    """Выполнить команду на удаленном сервере."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Команда: {command}")
    print()
    
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && {command}")
    
    # Выводим результаты в реальном времени
    while True:
        line = stdout.readline()
        if not line:
            break
        try:
            print(line.rstrip())
        except:
            pass  # Skip encoding errors
    
    # Проверяем ошибки
    error_output = stderr.read().decode('utf-8', errors='ignore')
    if error_output:
        print("\n[ERROR OUTPUT]:")
        print(error_output)
    
    exit_status = stdout.channel.recv_exit_status()
    return exit_status


def main():
    print("=" * 60)
    print("УЛУЧШЕННЫЙ БЭКТЕСТ С FILTER ПО CONFIDENCE")
    print("=" * 60)
    
    # Подключаемся
    print(f"\nПодключение к {SERVER}:{PORT}...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER, port=PORT, username=USER, password=PASSWORD, timeout=30)
        print("[OK] Подключено")
    except Exception as e:
        print(f"[ERROR] Ошибка подключения: {e}")
        return 1
    
    try:
        # Проверяем какая команда python доступна
        stdin, stdout, stderr = ssh.exec_command("which python3 python 2>/dev/null | head -1")
        python_cmd = stdout.read().decode().strip() or "python3"
        print(f"\nИспользуем: {python_cmd}")
        
        # Запускаем улучшенный бэктест
        print("\n[1/1] Запуск улучшенного бэктеста...")
        exit_status = execute_remote_command(
            ssh,
            f"{python_cmd} scripts/run_comprehensive_backtest.py --coins 20",
            "Тестирование модели с фильтрацией по confidence (min=0.60)"
        )
        
        print("\n" + "=" * 60)
        if exit_status == 0:
            print("[SUCCESS] Бэктест выполнен успешно!")
        else:
            print(f"[WARNING] Бэктест завершился с кодом {exit_status}")
        print("=" * 60)
        
    finally:
        ssh.close()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)

