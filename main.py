"""
Main entry point for the Random Chat Telegram Bot.

This module initializes the bot, sets up handlers, connects to MongoDB,
and starts the polling loop.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.settings import settings
from database.mongodb import init_db, close_db
from handlers import (
    start,
    chat,
    files,
    moderation,
    monetization,
    admin
)
from middlewares.auth import AuthMiddleware


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """
    Execute actions on bot startup.
    
    Args:
        bot: Bot instance
    """
    logger.info("Starting Random Chat Bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database connected successfully")
    
    # Set bot commands
    from aiogram.types import BotCommand, BotCommandScopeDefault
    
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="newchat", description="Find a random chat partner"),
        BotCommand(command="end", description="End current chat"),
        BotCommand(command="profile", description="View your profile"),
        BotCommand(command="settings", description="Update preferences"),
        BotCommand(command="help", description="Show help message"),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(bot: Bot) -> None:
    """
    Execute actions on bot shutdown.
    
    Args:
        bot: Bot instance
    """
    logger.info("Shutting down bot...")
    
    # Close database connection
    await close_db()
    logger.info("Database connection closed")
    
    logger.info("Bot stopped")


async def main() -> None:
    """Main function to start the bot."""
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Register middlewares
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(monetization.router)
    dp.include_router(chat.router)
    dp.include_router(files.router)
    dp.include_router(moderation.router)
    dp.include_router(admin.router)
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    except Exception as e:
        logger.error(f"Error during polling: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)