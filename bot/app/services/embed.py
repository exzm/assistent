from __future__ import annotations

from openai import AsyncOpenAI

from app.config import Settings, get_settings
from app.services.proxyapi import get_openai_client
from app.utils.vectors import normalize_vector


def build_embed_input(title: str | None, summary: str | None, raw_text: str | None) -> str:
    parts = [part for part in (title, summary, raw_text) if part]
    return "\n".join(parts)[:8000]


def prepare_embed_text(text: str | None) -> str:
    cleaned = " ".join((text or "").split())
    return cleaned[:8000] if cleaned else "empty"


async def embed_text(
    text: str,
    *,
    client: AsyncOpenAI | None = None,
    settings: Settings | None = None,
) -> list[float]:
    cfg = settings or get_settings()
    openai_client = client or get_openai_client(cfg)
    payload = prepare_embed_text(text)
    kwargs = {"model": cfg.model_embed, "input": payload}

    try:
        response = await openai_client.embeddings.create(
            **kwargs,
            dimensions=cfg.embed_dimensions,
        )
    except Exception:
        response = await openai_client.embeddings.create(**kwargs)

    return normalize_vector(list(response.data[0].embedding), cfg.embed_dimensions)
