from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from app.domain.payload import PendingPayload
from app.services import stt, vision


def is_audio_payload(payload: PendingPayload) -> bool:
    return payload.source_type == "voice" or (payload.mime_type or "").startswith("audio/")


def is_image_payload(payload: PendingPayload) -> bool:
    return payload.source_type in {"photo", "image"} or (payload.mime_type or "").startswith("image/")


async def materialize_query_text(payload: PendingPayload) -> str:
    text = (payload.query_text or payload.text or payload.caption or "").strip()
    if text:
        return text
    if not payload.file_bytes:
        return ""

    suffix = f".{payload.file_ext or 'bin'}"
    with NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(payload.file_bytes)
        tmp.flush()
        path = Path(tmp.name)
        if is_audio_payload(payload):
            return (await stt.transcribe_audio(path)).strip()
        if is_image_payload(payload):
            return (await vision.describe_image(path, caption=payload.caption)).strip()
    return ""
