from __future__ import annotations

from pathlib import Path

from openai import AsyncOpenAI

from app.config import Settings, get_settings
from app.services.proxyapi import get_openai_client


async def transcribe_audio(
    file_path: str | Path,
    *,
    client: AsyncOpenAI | None = None,
    settings: Settings | None = None,
) -> str:
    cfg = settings or get_settings()
    openai_client = client or get_openai_client(cfg)
    path = Path(file_path)
    with path.open("rb") as audio_file:
        result = await openai_client.audio.transcriptions.create(
            model=cfg.model_stt,
            file=audio_file,
        )
    return (result.text or "").strip()
