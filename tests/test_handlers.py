from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.payload import PendingPayload
from app.handlers import callbacks, commands, incoming
from app.handlers.forwarding import (
    format_user_name,
    forward_from_message,
    is_forward_message,
    resolve_source_type,
)
from app.keyboards import pending_action_keyboard
from tests.conftest import make_item, mock_message


def test_forwarding_helpers():
    assert format_user_name("A", "B", "u") == "A B (@u)"
    assert format_user_name(None, None, "u") == "@u"
    assert format_user_name(None, None, None) == "unknown"

    msg = mock_message(forward_from=SimpleNamespace(first_name="A", last_name=None, username=None))
    assert forward_from_message(msg) == "A"
    msg = mock_message(forward_from_chat=SimpleNamespace(title="Chat", id=1))
    assert forward_from_message(msg) == "Chat"
    msg = mock_message(forward_sender_name="Hidden")
    assert forward_from_message(msg) == "Hidden"
    msg = mock_message(
        forward_origin=SimpleNamespace(
            sender_user=SimpleNamespace(first_name="X", last_name="Y", username=None),
            chat=None,
            sender_chat=None,
            sender_user_name=None,
        )
    )
    assert forward_from_message(msg) == "X Y"
    msg = mock_message(
        forward_origin=SimpleNamespace(
            sender_user=None,
            chat=SimpleNamespace(title=None, id=99),
            sender_chat=None,
            sender_user_name=None,
        )
    )
    assert forward_from_message(msg) == "99"
    msg = mock_message(
        forward_origin=SimpleNamespace(
            sender_user=None,
            chat=None,
            sender_chat=None,
            sender_user_name="Anon",
        )
    )
    assert forward_from_message(msg) == "Anon"
    msg = mock_message(forward_origin=SimpleNamespace(sender_user=None, chat=None, sender_chat=None, sender_user_name=None))
    assert forward_from_message(msg) is None
    assert is_forward_message(mock_message(forward_date=1))
    assert resolve_source_type(mock_message(), "text") == "text"


def test_keyboard():
    kb = pending_action_keyboard("abc")
    assert kb.inline_keyboard[0][0].callback_data == "act:save:abc"


@pytest.mark.asyncio
async def test_incoming_handlers():
    message = mock_message(
        voice=SimpleNamespace(file_id="v", mime_type=None),
        caption="cap",
    )
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await incoming.on_voice(message)
        message.answer.assert_awaited()

    message = mock_message(
        audio=SimpleNamespace(file_id="a", mime_type=None, file_name="song.wav"),
    )
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await incoming.on_audio(message)

    message = mock_message(
        photo=[SimpleNamespace(file_id="p1"), SimpleNamespace(file_id="p2")],
        caption="photo-cap",
    )
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await incoming.on_photo(message)

    message = mock_message(
        document=SimpleNamespace(file_id="d", file_name=None, mime_type="image/png"),
        caption="doc",
    )
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await incoming.on_document(message)

    message = mock_message(document=SimpleNamespace(file_id="d", file_name="a.pdf", mime_type=None))
    with patch("app.handlers.incoming.download_telegram_file", AsyncMock(return_value=b"1")):
        await incoming.on_document(message)

    message = mock_message(text="/start")
    await incoming.on_text(message)
    message = mock_message(text="   ")
    await incoming.on_text(message)
    message = mock_message(text="x" * 600)
    await incoming.on_text(message)
    assert message.answer.await_count == 1


@pytest.mark.asyncio
async def test_commands():
    message = mock_message()
    await commands.cmd_start(message)

    session = MagicMock()
    with patch("app.db.repository.list_recent", AsyncMock(return_value=[])):
        await commands.cmd_recent(message, session)
    with patch("app.db.repository.list_recent", AsyncMock(return_value=[make_item()])):
        await commands.cmd_recent(message, session)

    command = SimpleNamespace(args=None)
    await commands.cmd_get(message, command, session)
    command = SimpleNamespace(args="9")
    with patch("app.db.repository.get_item", AsyncMock(return_value=None)):
        await commands.cmd_get(message, command, session)
    with patch("app.db.repository.get_item", AsyncMock(return_value=make_item(file_path=None))):
        await commands.cmd_get(message, command, session)
    with patch("app.db.repository.get_item", AsyncMock(return_value=make_item(file_path="/nope"))):
        message.answer_document = AsyncMock(side_effect=OSError("x"))
        await commands.cmd_get(message, command, session)
    with patch("app.db.repository.get_item", AsyncMock(return_value=make_item(file_path="/tmp/x"))):
        message.answer_document = AsyncMock()
        await commands.cmd_get(message, command, session)

    command = SimpleNamespace(args="")
    await commands.cmd_ask(message, command, session)
    status = MagicMock()
    status.edit_text = AsyncMock()
    message.answer = AsyncMock(return_value=status)
    command = SimpleNamespace(args="when oil?")
    with patch("app.handlers.commands.answer_question", AsyncMock(return_value=("ans", []))):
        await commands.cmd_ask(message, command, session)
    with patch("app.handlers.commands.answer_question", AsyncMock(side_effect=RuntimeError("boom"))):
        await commands.cmd_ask(message, command, session)


@pytest.mark.asyncio
async def test_callbacks():
    assert callbacks.parse_action_data(None) is None
    assert callbacks.parse_action_data("bad") is None
    assert callbacks.parse_action_data("act:save:id1") == ("save", "id1")

    callback = MagicMock()
    callback.data = "act:save:missing"
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.from_user = SimpleNamespace(id=42)
    callback.bot = MagicMock()
    callback.bot.send_message = AsyncMock()

    await callbacks.on_action(callback, MagicMock())

    payload = PendingPayload(source_type="text", text="q", query_text="q")
    with patch("app.handlers.callbacks.pop_pending", return_value=payload):
        callback.data = "act:cancel:id"
        await callbacks.on_action(callback, MagicMock())

        callback.data = "act:unknown:id"
        await callbacks.on_action(callback, MagicMock())

        with patch("app.handlers.callbacks.ingest_payload", AsyncMock(return_value=make_item())):
            callback.data = "act:save:id"
            await callbacks.on_action(callback, MagicMock())

        with patch("app.handlers.callbacks.ingest_payload", AsyncMock(side_effect=RuntimeError("x"))):
            callback.data = "act:save:id"
            with patch("app.handlers.callbacks.pop_pending", return_value=payload):
                await callbacks.on_action(callback, MagicMock())

        with patch("app.handlers.callbacks.materialize_query_text", AsyncMock(return_value="q")):
            with patch("app.handlers.callbacks.answer_question", AsyncMock(return_value=("a", []))):
                callback.data = "act:ask:id"
                with patch("app.handlers.callbacks.pop_pending", return_value=payload):
                    await callbacks.on_action(callback, MagicMock())

        with patch("app.handlers.callbacks.materialize_query_text", AsyncMock(return_value="")):
            callback.data = "act:ask:id"
            with patch("app.handlers.callbacks.pop_pending", return_value=payload):
                await callbacks.on_action(callback, MagicMock())

        with patch("app.handlers.callbacks.materialize_query_text", AsyncMock(side_effect=RuntimeError("x"))):
            callback.data = "act:ask:id"
            with patch("app.handlers.callbacks.pop_pending", return_value=payload):
                await callbacks.on_action(callback, MagicMock())

        with patch("app.handlers.callbacks.materialize_query_text", AsyncMock(return_value="q")):
            with patch("app.handlers.callbacks.answer_question", AsyncMock(side_effect=RuntimeError("x"))):
                callback.data = "act:ask:id"
                with patch("app.handlers.callbacks.pop_pending", return_value=payload):
                    await callbacks.on_action(callback, MagicMock())

    callback.data = "act:x"
    await callbacks.on_action(callback, MagicMock())

    callback.message = None
    await callbacks.edit_or_send(callback, "hi")
