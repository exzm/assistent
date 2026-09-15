from app.config import Settings, clear_settings_cache, get_settings
from app.exceptions import ConfigurationError, HelperBotError, IngestError, QueryError
from app.services.proxyapi import get_openai_client, reset_openai_client, set_openai_client


def test_settings_load(settings):
    assert settings.telegram_user_id == 42
    assert settings.embed_dimensions == 4
    assert get_settings() is settings


def test_clear_settings_cache(monkeypatch):
    clear_settings_cache()
    monkeypatch.setenv("TELEGRAM_USER_ID", "99")
    clear_settings_cache()
    assert get_settings().telegram_user_id == 99


def test_openai_client_singleton(settings):
    reset_openai_client()
    first = get_openai_client(settings)
    second = get_openai_client()
    assert first is second
    set_openai_client(None)
    reset_openai_client()
    third = get_openai_client(settings)
    assert third is not first


def test_exception_hierarchy():
    assert issubclass(ConfigurationError, HelperBotError)
    assert issubclass(IngestError, HelperBotError)
    assert issubclass(QueryError, HelperBotError)
    assert str(HelperBotError("x")) == "x"


def test_settings_model_defaults():
    cfg = Settings(
        telegram_bot_token="t",
        telegram_user_id=1,
        proxyapi_api_key="k",
    )
    assert cfg.proxyapi_base_url.startswith("https://")
