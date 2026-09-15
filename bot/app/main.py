from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app.config import Settings, get_settings
from app.middleware import create_dispatcher, setup_logging, wait_for_db
from app.services.storage import ensure_files_dir


async def run_bot(settings: Settings | None = None) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    cfg = settings or get_settings()

    ensure_files_dir(cfg)
    await wait_for_db()

    bot = Bot(token=cfg.telegram_bot_token)
    dp = create_dispatcher(cfg)
    logger.info("Bot starting (long polling), allowed user_id=%s", cfg.telegram_user_id)
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
