#!/usr/bin/env python3
"""Initialize database tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from app.database import engine, Base
from app.models.user import User, Subscription
from app.models.signal import Signal
from app.models.trade import Trade
from app.models.token import Token


async def init_db():
    """Create all database tables."""
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
