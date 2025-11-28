"""
Репозиторий для работы с токенами.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.models.token import Token, TokenPool


class TokenRepository:
    """Репозиторий для токенов."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_address(self, address: str, chain: str) -> Optional[Token]:
        """Получить токен по адресу."""
        result = await self.db.execute(
            select(Token).where(
                Token.address == address.lower(),
                Token.chain == chain
            )
        )
        return result.scalar_one_or_none()
    
    async def create(self, token_data: dict) -> Token:
        """Создать новый токен."""
        token = Token(**token_data)
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token
    
    async def update(self, token: Token, update_data: dict) -> Token:
        """Обновить токен."""
        for key, value in update_data.items():
            setattr(token, key, value)
        await self.db.commit()
        await self.db.refresh(token)
        return token
    
    async def get_pools_by_token(self, token_id: int) -> List[TokenPool]:
        """Получить пулы токена."""
        result = await self.db.execute(
            select(TokenPool).where(TokenPool.token_id == token_id)
        )
        return list(result.scalars().all())
    
    async def create_pool(self, pool_data: dict) -> TokenPool:
        """Создать новый пул."""
        pool = TokenPool(**pool_data)
        self.db.add(pool)
        await self.db.commit()
        await self.db.refresh(pool)
        return pool

