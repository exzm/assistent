from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.services.proxyapi import get_openai_client


async def transcribe_audio(file_path: str | Path) -> str:
    settings = get_settings()
    client = get_openai_client()
    path = Path(file_path)
    with path.open("rb") as audio_file:
        result = await client.audio.transcriptions.create(
            model=settings.model_stt,
            file=audio_file,
        )
    return (result.text or "").strip()
