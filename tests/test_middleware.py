from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Message

from app.middleware import (
    DbSessionMiddleware,
    WhitelistMiddleware,
    create_dispatcher,
    extract_user_id,
    reject_unauthorized,
    setup_logging,
    wait_for_db,
)


@pytest.mark.asyncio
async def test_whitelist_middleware_allows_and_blocks(settings):
    mw = WhitelistMiddleware(allowed_user_id=42)
    handler = AsyncMock(return_value="ok")

    allowed = MagicMock(spec=Message)
    allowed.from_user = SimpleNamespace(id=42)
    allowed.answer = AsyncMock()
    assert await mw(handler, allowed, {}) == "ok"

    denied = MagicMock(spec=Message)
    denied.from_user = SimpleNamespace(id=7)
    denied.answer = AsyncMock()
    assert await mw(handler, denied, {}) is None
    denied.answer.assert_awaited()

    denied_cb = MagicMock(spec=CallbackQuery)
    denied_cb.from_user = SimpleNamespace(id=7)
    denied_cb.answer = AsyncMock()
    assert await mw(handler, denied_cb, {}) is None

    weird = object()
    assert extract_user_id(weird) is None  # type: ignore[arg-type]
    await reject_unauthorized(weird)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_db_session_middleware_and_wait_for_db():
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    factory = MagicMock(return_value=session)

    mw = DbSessionMiddleware(session_factory=factory)
    handler = AsyncMock(return_value="done")
    data: dict = {}
    assert await mw(handler, object(), data) == "done"
    assert data["session"] is session

    sleeper = AsyncMock()
    await wait_for_db(retries=1, delay=0, session_factory=factory, sleeper=sleeper)

    failing = MagicMock(side_effect=RuntimeError("down"))
    with pytest.raises(RuntimeError, match="Database is not ready"):
        await wait_for_db(retries=2, delay=0, session_factory=failing, sleeper=AsyncMock())


def test_setup_logging_and_dispatcher(settings):
    setup_logging()
    dp = create_dispatcher(settings)
    assert dp is not None
