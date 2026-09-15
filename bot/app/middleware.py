from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings, get_settings
from app.db.session import SessionLocal

if TYPE_CHECKING:
    from aiogram import Dispatcher


class WhitelistMiddleware(BaseMiddleware):
    """Allow only the configured Telegram user."""

    def __init__(self, allowed_user_id: int | None = None) -> None:
        self._allowed_user_id = allowed_user_id

    def _resolve_allowed_id(self) -> int:
        if self._allowed_user_id is not None:
            return self._allowed_user_id
        return get_settings().telegram_user_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        allowed_id = self._resolve_allowed_id()
        user_id = extract_user_id(event)

        # TELEGRAM_USER_ID=0 enables one-time bootstrap: show caller id and block.
        if allowed_id == 0:
            await reveal_user_id(event)
            return None

        if user_id is None or user_id != allowed_id:
            await reject_unauthorized(event)
            return None
        return await handler(event, data)


def extract_user_id(event: TelegramObject) -> int | None:
    if isinstance(event, Message) and event.from_user:
        return event.from_user.id
    if isinstance(event, CallbackQuery) and event.from_user:
        return event.from_user.id
    return None


async def reject_unauthorized(event: TelegramObject) -> None:
    if isinstance(event, Message):
        await event.answer("Access denied.")
    elif isinstance(event, CallbackQuery):
        await event.answer("Access denied.", show_alert=True)


async def reveal_user_id(event: TelegramObject) -> None:
    logger = logging.getLogger(__name__)
    user_id = extract_user_id(event)
    if user_id is not None:
        logger.info("Bootstrap detected telegram user_id=%s", user_id)
    text = (
        f"Bootstrap mode.\nYour Telegram user id: {user_id}\n"
        "Set TELEGRAM_USER_ID in .env and restart the bot."
        if user_id is not None
        else "Bootstrap mode. Could not detect user id."
    )
    if isinstance(event, Message):
        await event.answer(text)
    elif isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=True)


class DbSessionMiddleware(BaseMiddleware):
    """Inject an AsyncSession into handler data."""

    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._session_factory() as session:
            data["session"] = session
            return await handler(event, data)


async def wait_for_db(
    retries: int = 30,
    delay: float = 2.0,
    *,
    session_factory=SessionLocal,
    sleeper: Callable[[float], Awaitable[None]] | None = None,
) -> None:
    from sqlalchemy import text

    sleep = sleeper or asyncio.sleep
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            await sleep(delay)
    raise RuntimeError(f"Database is not ready: {last_error}")


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )


def create_dispatcher(settings: Settings | None = None) -> Dispatcher:
    from aiogram import Dispatcher

    from app.handlers import callbacks, commands, incoming

    cfg = settings or get_settings()
    dp = Dispatcher()
    dp.message.middleware(WhitelistMiddleware(cfg.telegram_user_id))
    dp.callback_query.middleware(WhitelistMiddleware(cfg.telegram_user_id))
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(incoming.router)
    return dp
