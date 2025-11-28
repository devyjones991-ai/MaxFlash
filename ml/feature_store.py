"""
Feature store для хранения и версионирования фич.
"""
import redis.asyncio as redis
from typing import Optional, Dict, Any
import json
from datetime import timedelta
from app.config import settings


class FeatureStore:
    """Хранилище фич с кэшированием в Redis."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Подключиться к Redis."""
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    async def disconnect(self):
        """Отключиться от Redis."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def get_features(
        self,
        token_address: str,
        feature_version: str = "v1"
    ) -> Optional[Dict[str, Any]]:
        """Получить фичи токена из кэша."""
        if not self.redis_client:
            await self.connect()
        
        key = f"features:{feature_version}:{token_address.lower()}"
        data = await self.redis_client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def store_features(
        self,
        token_address: str,
        features: Dict[str, Any],
        feature_version: str = "v1",
        ttl: int = 3600
    ):
        """Сохранить фичи токена в кэш."""
        if not self.redis_client:
            await self.connect()
        
        key = f"features:{feature_version}:{token_address.lower()}"
        await self.redis_client.setex(
            key,
            ttl,
            json.dumps(features)
        )
    
    async def invalidate_features(self, token_address: str, feature_version: str = "v1"):
        """Удалить фичи из кэша."""
        if not self.redis_client:
            await self.connect()
        
        key = f"features:{feature_version}:{token_address.lower()}"
        await self.redis_client.delete(key)

