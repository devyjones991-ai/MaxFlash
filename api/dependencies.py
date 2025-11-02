"""
Зависимости для FastAPI endpoints.
"""
from typing import Optional
from fastapi import Header, HTTPException
import os


async def get_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Проверка API ключа (опционально).
    
    Args:
        x_api_key: API ключ из заголовка
        
    Returns:
        API ключ
    """
    # В production использовать реальную проверку
    required_key = os.getenv("API_KEY")
    
    if required_key and x_api_key != required_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return x_api_key or "public"

