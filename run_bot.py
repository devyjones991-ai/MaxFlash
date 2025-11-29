#!/usr/bin/env python3
import os
import sys
import asyncio
import logging

#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bots.telegram.bot import TelegramBot
from app.database import AsyncSessionLocal
from utils.logger_config import setup_logging

# Setup logging
logger = setup_logging()


def main():
    """Run the Telegram bot."""
    try:
        logger.info("Starting Telegram Bot (LLM Integrated)...")
        from app.config import settings

        logger.info(f"Using database: {settings.DATABASE_URL}")

        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create DB session
        async def create_session():
            return AsyncSessionLocal()

        db = loop.run_until_complete(create_session())

        # Initialize bot
        bot = TelegramBot(db=db)

        # Check if token is configured
        if not bot.token:
            logger.error("TELEGRAM_BOT_TOKEN not configured. Please set it in .env file")
            sys.exit(1)

        # Start bot (blocking)
        logger.info("Starting bot polling...")
        bot.start()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running Telegram bot: {e}", exc_info=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
