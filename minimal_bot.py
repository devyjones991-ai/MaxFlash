import logging
import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I am a minimal bot running on the server. If you see this, connectivity is working!"
    )


async def main() -> None:
    """Start the bot."""
    # Hardcoded token for testing or load from env
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No token found!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))

    logger.info("Starting minimal bot polling...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
