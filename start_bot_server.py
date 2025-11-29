#!/usr/bin/env python3
"""Запуск Telegram бота на сервере"""
import paramiko
import sys
import time

def start_bot():
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
        
        # Проверка текущих процессов
        print("="*60)
        print("1. Проверка текущих процессов")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'run_bot.py' | grep -v grep")
        output = stdout.read().decode()
        if output:
            print("Найден запущенный процесс:")
            print(output)
            # Остановка
            stdin2, stdout2, stderr2 = ssh.exec_command("ps aux | grep 'run_bot.py' | grep -v grep | awk '{print $2}' | xargs kill")
            time.sleep(2)
            print("✅ Старые процессы остановлены")
        else:
            print("Запущенных процессов не найдено")
        
        # Запуск бота в фоне
        print("\n" + "="*60)
        print("2. Запуск Telegram бота")
        print("="*60)
        cmd = """
cd ~/MaxFlash && \
source venv/bin/activate && \
nohup python run_bot.py > logs/telegram_bot.log 2>&1 &
sleep 1 && \
ps aux | grep 'run_bot.py' | grep -v grep
"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        errors = stderr.read().decode()
        
        if output and "run_bot.py" in output:
            print("✅ Бот запущен:")
            print(output)
        else:
            print("⚠️ Не удалось подтвердить запуск")
            if errors:
                print("Ошибки:", errors)
        
        # Проверка логов через 3 секунды
        time.sleep(3)
        print("\n" + "="*60)
        print("3. Последние логи бота")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && tail -30 logs/telegram_bot.log 2>/dev/null || echo 'Логи пока пусты'")
        log_output = stdout.read().decode()
        print(log_output)
        
        # Финальная проверка процесса
        print("\n" + "="*60)
        print("4. Финальная проверка")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'run_bot.py' | grep -v grep")
        final_check = stdout.read().decode()
        if final_check:
            print("✅ Бот работает:")
            print(final_check)
        else:
            print("❌ Бот не запущен. Проверьте логи выше.")
        
        ssh.close()
        print("\n" + "="*60)
        print("Проверка завершена")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    start_bot()

