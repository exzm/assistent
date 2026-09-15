from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(min_length=1)
    telegram_user_id: int

    proxyapi_api_key: str = Field(min_length=1)
    proxyapi_base_url: str = "https://api.proxyapi.ru/v1"

    model_vision: str = "inclusionai/ling-3.0-flash-vl"
    model_vision_fallback: str = "z-ai/glm-5.3-flash"
    model_stt: str = "openai/gpt-4o-mini-transcribe"
    model_embed: str = "qwen/qwen3-embedding-8b"
    model_chat: str = "deepseek/deepseek-v4.1-flash"
    model_extract: str = "z-ai/glm-5.3-flash"

    database_url: str = "postgresql+asyncpg://helper:helper@db:5432/helper_bot"
    files_dir: str = "/data/files"

    embed_dimensions: int = Field(default=1024, gt=0)
    rag_top_k: int = Field(default=5, gt=0)
    pending_ttl_seconds: int = Field(default=3600, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Reset cached settings (useful in tests)."""
    get_settings.cache_clear()
