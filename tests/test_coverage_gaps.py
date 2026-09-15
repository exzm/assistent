from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message

from app.db.session import (
    SessionLocal,
    get_engine,
    get_session,
    get_session_factory,
    reset_db_engine,
)
from app.middleware import WhitelistMiddleware
from app.services.cards import format_item_card
from app.services.vision import build_vision_messages
from app.utils.parsing import extract_json_object


@pytest.mark.asyncio
async def test_session_lazy_factory(settings):
    reset_db_engine()
    fake_engine = object()
    fake_factory = MagicMock()
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    fake_factory.return_value = session

    with (
        patch("app.db.session.create_async_engine", return_value=fake_engine) as create_engine,
        patch("app.db.session.async_sessionmaker", return_value=fake_factory) as make_factory,
    ):
        assert get_engine(settings) is fake_engine
        assert get_session_factory(settings) is fake_factory
        assert get_engine() is fake_engine
        assert SessionLocal() is session
        create_engine.assert_called_once()
        make_factory.assert_called_once()

    with patch("app.db.session.get_session_factory", return_value=MagicMock(return_value=session)):
        gen = get_session()
        value = await gen.__anext__()
        assert value is session
        await gen.aclose()


@pytest.mark.asyncio
async def test_whitelist_uses_settings(settings):
    mw = WhitelistMiddleware()
    handler = AsyncMock(return_value="ok")
    msg = MagicMock(spec=Message)
    msg.from_user = SimpleNamespace(id=42)
    msg.answer = AsyncMock()
    assert await mw(handler, msg, {}) == "ok"


def test_cards_minimal_and_parsing_edge_cases(tmp_path):
    item = SimpleNamespace(
        id=1,
        title="T",
        event_date=None,
        amount=Decimal("1"),
        currency=None,
        category=None,
        tags=None,
        summary=None,
    )
    card = format_item_card(item)
    assert "Amount: 1" in card

    assert extract_json_object("{not json}") == {}
    path = tmp_path / "x.jpg"
    path.write_bytes(b"abc")
    messages = build_vision_messages(path)
    assert messages[0]["content"][0]["text"]


@pytest.mark.asyncio
async def test_incoming_branch_coverage():
    from app.handlers.incoming import on_audio, on_document, on_photo
    from helpers import mock_message

    message = mock_message(audio=SimpleNamespace(file_id="a", mime_type="audio/mpeg", file_name=None))
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await on_audio(message)

    message = mock_message(photo=[SimpleNamespace(file_id="p")], caption=None)
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await on_photo(message)

    message = mock_message(
        document=SimpleNamespace(file_id="d", file_name="x.bin", mime_type="application/octet-stream"),
        caption=None,
    )
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await on_document(message)
