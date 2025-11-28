"""
Единый файл запуска MaxFlash Trading System.
Запускает веб-интерфейс и Telegram бота с сигналами.
"""
import sys
import os
from pathlib import Path

# Настройка путей - корень проекта ПЕРВЫМ для импорта api
root = Path(__file__).parent.absolute()
os.chdir(root)

if str(root) not in sys.path:
    sys.path.insert(0, str(root))
if str(root / "web_interface") not in sys.path:
    sys.path.insert(1, str(root / "web_interface"))

# Переходим в web_interface для запуска app.py
os.chdir(root / "web_interface")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🚀 MAXFLASH - ТОРГОВАЯ СИСТЕМА")
    print("="*60)
    print("  🌐 Веб-интерфейс: http://localhost:8050")
    print("  🤖 Telegram бот: t.me/MaxFlash_bot")
    print("  ⏹️  Нажмите Ctrl+C для остановки")
    print("="*60 + "\n")

    try:
        import runpy
        runpy.run_path('app.py', run_name='__main__')
    except KeyboardInterrupt:
        print("\n✅ Остановка сервера...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

