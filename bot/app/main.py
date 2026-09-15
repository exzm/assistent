from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.config import get_settings
from app.db_middleware import DbSessionMiddleware, setup_logging, wait_for_db
from app.handlers import callbacks, commands, incoming
from app.middleware import WhitelistMiddleware
from app.services.storage import ensure_files_dir


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    ensure_files_dir()
    await wait_for_db()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.message.middleware(WhitelistMiddleware())
    dp.callback_query.middleware(WhitelistMiddleware())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(incoming.router)

    logger.info("Bot starting (long polling), allowed user_id=%s", settings.telegram_user_id)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
