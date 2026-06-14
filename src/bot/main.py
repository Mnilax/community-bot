"""Bot entry point — startup, shutdown, router registration."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.config import load_config
from bot.db import Database
from bot.handlers import admin, join, messages
from bot.services.antispam import AntiSpamService
from bot.services.captcha import CaptchaService
from bot.services.raid import RaidDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Initialize and start the bot."""
    config = load_config()

    if not config.bot_token:
        logger.error("BOT_TOKEN not set. Check your .env file.")
        return

    # Initialize services
    db = Database(config.database_path)
    await db.connect()

    antispam = AntiSpamService(
        rate_limit=config.flood_rate_limit,
        window_seconds=config.flood_window_seconds,
    )
    captcha = CaptchaService(
        timeout=config.captcha_timeout,
        captcha_type=config.captcha_type,
    )
    raid = RaidDetector(
        threshold=config.raid_join_threshold,
        lockdown_minutes=config.raid_lockdown_minutes,
    )

    # Initialize bot and dispatcher
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    # Register handlers
    join_router = join.setup(bot, db, captcha, raid, config)
    msg_router = messages.setup(bot, db, antispam)
    admin_router = admin.setup(bot, db, config.admin_ids, raid)

    dp.include_router(admin_router)  # Admin commands first
    dp.include_router(join_router)
    dp.include_router(msg_router)    # Catch-all last

    # Global error handler
    @dp.error()
    async def global_error_handler(event, exception):
        logger.error(f"Unhandled error: {exception}", exc_info=True)

    # Start polling
    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
