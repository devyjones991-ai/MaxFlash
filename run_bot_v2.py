#!/usr/bin/env python3
"""
Run MaxFlash Telegram Bot v2.0 - User-Friendly Edition
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from bots.telegram.bot_v2 import MaxFlashBotV2
from utils.logger_config import setup_logging

logger = setup_logging()


def main():
    """Run the bot."""
    logger.info("=" * 50)
    logger.info("MaxFlash Bot v2.0 - Starting...")
    logger.info("=" * 50)
    
    try:
        bot = MaxFlashBotV2()
        bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()





