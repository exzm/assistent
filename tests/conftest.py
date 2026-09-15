from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import clear_settings_cache
from app.services.pending import reset_pending_store
from app.services.proxyapi import reset_openai_client


@pytest.fixture(autouse=True)
def _clean_globals(monkeypatch, tmp_path):
    clear_settings_cache()
    reset_openai_client()
    reset_pending_store()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_USER_ID", "42")
    monkeypatch.setenv("PROXYAPI_API_KEY", "sk-test")
    monkeypatch.setenv("FILES_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("EMBED_DIMENSIONS", "4")
    monkeypatch.setenv("PENDING_TTL_SECONDS", "3600")
    clear_settings_cache()
    yield
    clear_settings_cache()
    reset_openai_client()
    reset_pending_store()


@pytest.fixture
def settings():
    from app.config import get_settings

    return get_settings()


def make_chat_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def make_embed_response(vector: list[float]) -> SimpleNamespace:
    return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])


def make_item(**kwargs):
    defaults = {
        "id": 1,
        "title": "Oil change",
        "event_date": None,
        "amount": None,
        "currency": None,
        "category": "auto_service",
        "tags": ["car"],
        "summary": "Changed oil",
        "raw_text": "Changed oil",
        "file_path": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def mock_message(**kwargs) -> MagicMock:
    message = MagicMock()
    message.message_id = kwargs.get("message_id", 1)
    message.caption = kwargs.get("caption")
    message.text = kwargs.get("text")
    message.forward_from = kwargs.get("forward_from")
    message.forward_from_chat = kwargs.get("forward_from_chat")
    message.forward_sender_name = kwargs.get("forward_sender_name")
    message.forward_date = kwargs.get("forward_date")
    message.forward_origin = kwargs.get("forward_origin")
    message.voice = kwargs.get("voice")
    message.audio = kwargs.get("audio")
    message.photo = kwargs.get("photo")
    message.document = kwargs.get("document")
    message.answer = AsyncMock()
    message.answer_document = AsyncMock()
    message.bot = MagicMock()
    message.bot.download = AsyncMock()
    return message
