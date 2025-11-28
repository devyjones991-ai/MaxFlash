# MaxFlash Trading System - Quick Start

## Установка

1. Клонируйте репозиторий (если нужно)
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл
```

## Запуск с Docker

1. Запустите сервисы:
```bash
docker-compose -f infra/docker-compose.yml up -d
```

2. Дождитесь готовности PostgreSQL и Redis

3. Запустите миграции:
```bash
alembic upgrade head
```

4. API будет доступен на http://localhost:8000

## Запуск без Docker

1. Установите PostgreSQL и Redis локально

2. Создайте базу данных:
```sql
CREATE DATABASE maxflash;
CREATE USER maxflash WITH PASSWORD 'maxflash_dev';
GRANT ALL PRIVILEGES ON DATABASE maxflash TO maxflash;
```

3. Запустите миграции:
```bash
alembic upgrade head
```

4. Запустите API:
```bash
uvicorn app.main:app --reload
```

## Компиляция Cython расширений

```bash
cd cython_ext
python setup.py build_ext --inplace
```

## Запуск тестов

```bash
pytest tests/ -v
```

## Структура проекта

- `app/` - FastAPI приложение
- `services/` - Бизнес-логика
- `bots/telegram/` - Telegram бот
- `ml/` - ML модели
- `cython_ext/` - Cython расширения
- `infra/` - Docker и инфраструктура
- `tests/` - Тесты

## Основные команды

- Генерация миграции: `alembic revision --autogenerate -m "description"`
- Применить миграции: `alembic upgrade head`
- Откатить миграцию: `alembic downgrade -1`
- Запуск тестов: `pytest tests/ -v`
- Заполнение данных: `python scripts/backfill_data.py`

## API Документация

После запуска API доступна на:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Telegram Bot

Для запуска Telegram бота:
```python
from bots.telegram.bot import TelegramBot
from app.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        bot = TelegramBot(db)
        bot.start()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Troubleshooting

1. **Ошибка подключения к БД**: Проверьте DATABASE_URL в .env
2. **Ошибка Redis**: Убедитесь что Redis запущен
3. **Ошибка импорта Cython**: Скомпилируйте расширения или используйте fallback на Python код

