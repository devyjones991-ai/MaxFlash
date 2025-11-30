#!/usr/bin/env python3
"""Исправление проблемы с Telegram ботом на сервере"""
import paramiko
import sys
import time

def fix_bot():
    hostname = "192.168.0.204"
    port = 22
    username = "devyjones"
    password = "19Maxon91!"
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Подключение к {hostname}...")
        ssh.connect(hostname, port=port, username=username, password=password, timeout=10)
        print("✅ Подключено успешно\n")
        
        # 1. Остановить текущий процесс бота
        print("="*60)
        print("1. Остановка текущего процесса бота")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'run_bot.py' | grep -v grep | awk '{print $2}'")
        pids = stdout.read().decode().strip()
        if pids:
            for pid in pids.split('\n'):
                if pid.strip():
                    print(f"Остановка процесса {pid.strip()}...")
                    ssh.exec_command(f"kill {pid.strip()}")
                    time.sleep(1)
            print("✅ Процессы остановлены")
        else:
            print("Процессы не найдены")
        
        # 2. Активировать venv и установить зависимости
        print("\n" + "="*60)
        print("2. Установка python-telegram-bot")
        print("="*60)
        cmd = """
cd ~/MaxFlash && \
source venv/bin/activate && \
pip install python-telegram-bot --quiet && \
echo "✅ Установка завершена"
"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        errors = stderr.read().decode()
        print(output)
        if errors and "error" in errors.lower():
            print("Ошибки:", errors)
        
        # 3. Проверка установки
        print("\n" + "="*60)
        print("3. Проверка установки")
        print("="*60)
        cmd = "cd ~/MaxFlash && source venv/bin/activate && python -c 'import telegram; print(f\"✅ python-telegram-bot версия: {telegram.__version__}\")'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        errors = stderr.read().decode()
        print(output)
        if errors:
            print("Ошибки:", errors)
        
        # 4. Проверка импорта модуля бота
        print("\n" + "="*60)
        print("4. Проверка импорта модуля бота")
        print("="*60)
        cmd = "cd ~/MaxFlash && source venv/bin/activate && python -c 'from bots.telegram.bot import TelegramBot; print(\"✅ Импорт успешен\")' 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        errors = stderr.read().decode()
        print(output)
        if errors and "error" in errors.lower() or "traceback" in errors.lower():
            print("❌ Ошибки импорта:")
            print(errors)
        
        # 5. Запуск бота в фоне
        print("\n" + "="*60)
        print("5. Запуск бота")
        print("="*60)
        cmd = """
cd ~/MaxFlash && \
source venv/bin/activate && \
nohup python run_bot.py > logs/telegram_bot.log 2>&1 &
echo $!
"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        pid = stdout.read().decode().strip()
        errors = stderr.read().decode()
        if pid:
            print(f"✅ Бот запущен с PID: {pid}")
        else:
            print("⚠️ Не удалось получить PID")
        if errors:
            print("Ошибки:", errors)
        
        # 6. Проверка запуска
        time.sleep(2)
        print("\n" + "="*60)
        print("6. Проверка запущенного процесса")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'run_bot.py' | grep -v grep")
        output = stdout.read().decode()
        if output:
            print("✅ Процесс запущен:")
            print(output)
        else:
            print("❌ Процесс не найден")
        
        # 7. Просмотр логов
        print("\n" + "="*60)
        print("7. Последние логи")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && tail -20 logs/telegram_bot.log 2>/dev/null || echo 'Логи пока пусты'")
        print(stdout.read().decode())
        
        ssh.close()
        print("\n" + "="*60)
        print("✅ Исправление завершено")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    fix_bot()

