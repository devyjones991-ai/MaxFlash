#!/usr/bin/env python3
"""
Запуск команд на удаленном сервере.
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
        print(line.rstrip())
    
    # Проверяем ошибки
    error_output = stderr.read().decode('utf-8', errors='ignore')
    if error_output:
        print("\n[ERROR OUTPUT]:")
        print(error_output)
    
    exit_status = stdout.channel.recv_exit_status()
    return exit_status


def main():
    print("=" * 60)
    print("ЗАПУСК КОМАНД НА СЕРВЕРЕ")
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
        # 1. Проверяем зависимости
        print("\n[1/4] Проверка зависимостей...")
        exit_status = execute_remote_command(
            ssh, 
            "pip install paramiko scp -q 2>&1 | tail -5",
            "Установка зависимостей (если нужно)"
        )
        
        # Проверяем какая команда python доступна
        stdin, stdout, stderr = ssh.exec_command("which python3 python 2>/dev/null | head -1")
        python_cmd = stdout.read().decode().strip() or "python3"
        print(f"\nИспользуем: {python_cmd}")
        
        # 2. Обучение модели
        print("\n[2/4] Обучение модели...")
        exit_status = execute_remote_command(
            ssh,
            f"{python_cmd} scripts/train_lightgbm.py --coins 20",
            "Обучение LightGBM модели с barrier-лейблами"
        )
        
        if exit_status != 0:
            print(f"\n[WARNING] Обучение завершилось с кодом {exit_status}")
        
        # Небольшая пауза
        time.sleep(2)
        
        # 3. Бэктест
        print("\n[3/4] Запуск бэктеста...")
        exit_status = execute_remote_command(
            ssh,
            f"{python_cmd} scripts/run_comprehensive_backtest.py --coins 20",
            "Тестирование модели на исторических данных"
        )
        
        if exit_status != 0:
            print(f"\n[WARNING] Бэктест завершился с кодом {exit_status}")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Команды выполнены!")
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

