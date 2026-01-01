#!/usr/bin/env python3
"""
Скрипт синхронизации файлов на сервер.
Использование: python scripts/sync_to_server.py
"""

import os
import sys
from pathlib import Path
import paramiko
from scp import SCPClient

# Конфигурация сервера
SERVER = "192.168.0.203"
PORT = 22
USER = "devyjones"
PASSWORD = "19Maxon91!"
REMOTE_PATH = "/home/devyjones/MaxFlash"

# Файлы для синхронизации
FILES = [
    # Новые файлы
    "ml/labeling.py",
    "trading/outcome_tracker.py",
    "utils/universe_selector.py",
    "utils/signal_integrator.py",
    "utils/advanced_signal_validator.py",
    "utils/enhanced_signal_generator.py",
    
    # Модифицированные файлы
    "ml/lightgbm_model.py",
    "bots/telegram/bot_v2.py",
    "scripts/train_lightgbm.py",
    "scripts/run_comprehensive_backtest.py",
    "scripts/auto_retrain_v2.py",
]

BASE_DIR = Path(__file__).parent.parent


def main():
    print("=" * 60)
    print("SYNC TO SERVER - MaxFlash Updates")
    print("=" * 60)
    print()
    
    # Подключаемся к серверу
    print(f"Подключение к {SERVER}:{PORT}...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER, port=PORT, username=USER, password=PASSWORD, timeout=10)
        print("[OK] Подключено")
        print()
    except Exception as e:
        print(f"[ERROR] Ошибка подключения: {e}")
        print("\nУбедитесь что:")
        print("  1. Сервер доступен")
        print("  2. SSH сервис запущен")
        print("  3. Установлен paramiko: pip install paramiko scp")
        return 1
    
    # Создаем директории
    print("Создание директорий...")
    dirs = set(os.path.dirname(f) for f in FILES if os.path.dirname(f))
    for d in dirs:
        remote_dir = f"{REMOTE_PATH}/{d}"
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p '{remote_dir}'")
        stdout.channel.recv_exit_status()
        print(f"  [OK] {d}")
    print()
    
    # Копируем файлы
    print("Копирование файлов...")
    success = 0
    failed = 0
    
    with SCPClient(ssh.get_transport()) as scp:
        for file_path in FILES:
            local_file = BASE_DIR / file_path
            
            if not local_file.exists():
                print(f"  [SKIP] {file_path} (не найден)")
                failed += 1
                continue
            
            remote_file = f"{REMOTE_PATH}/{file_path}"
            remote_dir = os.path.dirname(remote_file)
            
            try:
                scp.put(str(local_file), remote_file)
                print(f"  [OK] {file_path}")
                success += 1
            except Exception as e:
                print(f"  [ERROR] {file_path}: {e}")
                failed += 1
    
    ssh.close()
    
    print()
    print("=" * 60)
    print("РЕЗУЛЬТАТ")
    print("=" * 60)
    print(f"Успешно: {success}")
    print(f"Ошибок:  {failed}")
    print()
    
    if failed == 0:
        print("[SUCCESS] Все файлы успешно синхронизированы!")
        print()
        print("Следующие шаги на сервере:")
        print(f"  1. ssh {USER}@{SERVER}")
        print(f"  2. cd {REMOTE_PATH}")
        print("  3. pip install -r requirements.txt  # если нужно")
        print("  4. python scripts/train_lightgbm.py --coins 20")
        print("  5. python scripts/run_comprehensive_backtest.py --coins 20")
        return 0
    else:
        print("[WARNING] Некоторые файлы не были скопированы")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)

