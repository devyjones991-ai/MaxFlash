"""
Скрипт для заполнения исторических данных.
"""
import asyncio
from app.database import AsyncSessionLocal, init_db
from services.dex_ingest.scanner_service import DEXScannerService


async def backfill_tokens():
    """Заполнить данные о токенах."""
    await init_db()
    
    async with AsyncSessionLocal() as db:
        scanner = DEXScannerService(db)
        
        # Пример: инжест популярных токенов
        popular_tokens = [
            ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "ethereum"),  # USDC
            ("0xdAC17F958D2ee523a2206206994597C13D831ec7", "ethereum"),  # USDT
        ]
        
        for token_address, chain in popular_tokens:
            try:
                await scanner.ingest_token_pools(token_address, chain)
                print(f"✓ Ingested {token_address} on {chain}")
            except Exception as e:
                print(f"✗ Error ingesting {token_address}: {e}")


if __name__ == "__main__":
    asyncio.run(backfill_tokens())

