from __future__ import annotations

from app.config import get_settings
from app.services.proxyapi import get_openai_client


async def embed_text(text: str) -> list[float]:
    settings = get_settings()
    client = get_openai_client()
    cleaned = " ".join((text or "").split())
    if not cleaned:
        cleaned = "empty"

    kwargs = {
        "model": settings.model_embed,
        "input": cleaned[:8000],
    }
    try:
        response = await client.embeddings.create(
            **kwargs,
            dimensions=settings.embed_dimensions,
        )
    except Exception:
        response = await client.embeddings.create(**kwargs)

    vector = list(response.data[0].embedding)
    dim = settings.embed_dimensions
    if len(vector) > dim:
        vector = vector[:dim]
    elif len(vector) < dim:
        vector = vector + [0.0] * (dim - len(vector))
    return vector


def build_embed_input(title: str | None, summary: str | None, raw_text: str | None) -> str:
    parts = [p for p in [title, summary, raw_text] if p]
    return "\n".join(parts)[:8000]
