#!/usr/bin/env python3
import os
import sys
import logging

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

        # Create DB session
        db = AsyncSessionLocal()

        # Initialize bot
        bot = TelegramBot(db=db)

        # Start bot (blocking)
        bot.start()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running Telegram bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
