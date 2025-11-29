#!/usr/bin/env python3
"""Проверка состояния Telegram бота на сервере"""
import paramiko
import sys

def check_server():
    hostname = "192.168.0.204"
    port = 22
    username = "devyjones"
    password = "19Maxon91!"
    
    try:
        # Подключение
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Подключение к {hostname}...")
        ssh.connect(hostname, port=port, username=username, password=password, timeout=10)
        print("✅ Подключено успешно\n")
        
        # Проверка файлов
        print("="*60)
        print("1. Проверка файлов проекта")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && pwd && ls -la run_bot.py bots/telegram/bot.py 2>&1")
        print(stdout.read().decode())
        if stderr.read():
            print("Ошибки:", stderr.read().decode())
        
        # Проверка процессов
        print("\n" + "="*60)
        print("2. Проверка запущенных процессов бота")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'run_bot|telegram|python.*bot' | grep -v grep || echo 'Процессы не найдены'")
        output = stdout.read().decode()
        print(output if output.strip() else "Процессы бота не запущены")
        
        # Проверка токена
        print("\n" + "="*60)
        print("3. Проверка конфигурации (TELEGRAM_BOT_TOKEN)")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && (cat .env 2>/dev/null | grep TELEGRAM_BOT_TOKEN || echo 'Токен не найден в .env')")
        print(stdout.read().decode())
        
        # Проверка переменных окружения
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && echo $TELEGRAM_BOT_TOKEN | head -c 20")
        token_check = stdout.read().decode().strip()
        if token_check:
            print(f"Токен в переменных окружения: {token_check}...")
        else:
            print("Токен не установлен в переменных окружения")
        
        # Проверка логов
        print("\n" + "="*60)
        print("4. Последние логи (если есть)")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && (tail -30 logs/*.log 2>/dev/null | tail -20 || echo 'Логи не найдены')")
        print(stdout.read().decode())
        
        # Проверка зависимостей
        print("\n" + "="*60)
        print("5. Проверка установленных зависимостей")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && python3 -c 'import telegram; print(f\"python-telegram-bot: {telegram.__version__}\")' 2>&1 || echo 'python-telegram-bot не установлен'")
        print(stdout.read().decode())
        
        # Попытка запуска с проверкой ошибок
        print("\n" + "="*60)
        print("6. Тестовая проверка импорта модулей")
        print("="*60)
        stdin, stdout, stderr = ssh.exec_command("cd ~/MaxFlash && python3 -c 'from bots.telegram.bot import TelegramBot; print(\"✅ Импорт успешен\")' 2>&1")
        import_output = stdout.read().decode()
        import_errors = stderr.read().decode()
        print(import_output)
        if import_errors:
            print("❌ Ошибки импорта:")
            print(import_errors)
        
        ssh.close()
        print("\n" + "="*60)
        print("Проверка завершена")
        print("="*60)
        
    except paramiko.AuthenticationException:
        print("❌ Ошибка аутентификации")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"❌ Ошибка SSH: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    check_server()

