from __future__ import annotations

from openai import AsyncOpenAI

from app.config import Settings, get_settings

_client: AsyncOpenAI | None = None


def get_openai_client(settings: Settings | None = None) -> AsyncOpenAI:
    """Return a shared AsyncOpenAI client pointed at ProxyAPI."""
    global _client
    if _client is None:
        cfg = settings or get_settings()
        _client = AsyncOpenAI(
            api_key=cfg.proxyapi_api_key,
            base_url=cfg.proxyapi_base_url,
        )
    return _client


def reset_openai_client() -> None:
    """Drop the cached client (useful in tests)."""
    global _client
    _client = None


def set_openai_client(client: AsyncOpenAI | None) -> None:
    """Inject a client instance (useful in tests)."""
    global _client
    _client = client
