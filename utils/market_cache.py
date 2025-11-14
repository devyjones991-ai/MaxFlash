"""
Продвинутое кэширование для рыночных данных.
Поддержка Redis для production и in-memory для development.
"""
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import threading
import hashlib

from utils.logger_config import setup_logging

logger = setup_logging()

# Попытка импортировать Redis (опционально)
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None


class MarketCache:
    """
    Продвинутый кэш для рыночных данных с поддержкой Redis.
    """

    def __init__(self, use_redis: bool = False, redis_host: str = 'localhost', redis_port: int = 6379):
        """
        Инициализация кэша.

        Args:
            use_redis: Использовать Redis для кэширования
            redis_host: Хост Redis
            redis_port: Порт Redis
        """
        self.use_redis = use_redis and HAS_REDIS
        self.memory_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.lock = threading.Lock()
        
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning("Redis unavailable, using memory cache: %s", str(e))
                self.use_redis = False
        else:
            self.redis_client = None
            logger.info("Using in-memory cache")

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Создать ключ кэша из аргументов."""
        key_parts = [prefix] + [str(arg) for arg in args]
        if kwargs:
            key_parts.append(json.dumps(kwargs, sort_keys=True))
        key_string = ':'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str, ttl_seconds: int = 300) -> Optional[Any]:
        """
        Получить значение из кэша.

        Args:
            key: Ключ кэша
            ttl_seconds: Время жизни в секундах

        Returns:
            Значение или None если истекло или не найдено
        """
        if self.use_redis and self.redis_client:
            try:
                cached = self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning("Redis get error: %s", str(e))

        # Fallback to memory cache
        with self.lock:
            if key in self.memory_cache:
                value, timestamp = self.memory_cache[key]
                if (datetime.now() - timestamp).total_seconds() < ttl_seconds:
                    return value
                else:
                    del self.memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """
        Сохранить значение в кэш.

        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl_seconds: Время жизни в секундах
        """
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    ttl_seconds,
                    json.dumps(value, default=str)
                )
                return
            except Exception as e:
                logger.warning("Redis set error: %s", str(e))

        # Fallback to memory cache
        with self.lock:
            self.memory_cache[key] = (value, datetime.now())
            # Очистка старых записей
            if len(self.memory_cache) > 10000:
                self._cleanup_old_entries(ttl_seconds)

    def _cleanup_old_entries(self, ttl_seconds: int):
        """Очистить старые записи из памяти."""
        current_time = datetime.now()
        keys_to_delete = [
            key for key, (_, timestamp) in self.memory_cache.items()
            if (current_time - timestamp).total_seconds() > ttl_seconds
        ]
        for key in keys_to_delete[:1000]:  # Удаляем по 1000 за раз
            del self.memory_cache[key]

    def clear(self, pattern: Optional[str] = None):
        """
        Очистить кэш.

        Args:
            pattern: Паттерн для очистки (только для Redis)
        """
        if self.use_redis and self.redis_client and pattern:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning("Redis clear error: %s", str(e))

        with self.lock:
            if pattern:
                # Простая фильтрация по паттерну для памяти
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
            else:
                self.memory_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша."""
        stats = {
            'type': 'redis' if self.use_redis else 'memory',
            'memory_entries': len(self.memory_cache)
        }
        
        if self.use_redis and self.redis_client:
            try:
                stats['redis_keys'] = self.redis_client.dbsize()
            except Exception:
                pass
        
        return stats

