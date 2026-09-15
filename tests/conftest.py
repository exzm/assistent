from __future__ import annotations

import pytest

from app.config import clear_settings_cache
from app.db.session import reset_db_engine
from app.services.pending import reset_pending_store
from app.services.proxyapi import reset_openai_client


@pytest.fixture(autouse=True)
def _clean_globals(monkeypatch, tmp_path):
    clear_settings_cache()
    reset_openai_client()
    reset_pending_store()
    reset_db_engine()

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
    reset_db_engine()


@pytest.fixture
def settings():
    from app.config import get_settings

    return get_settings()
