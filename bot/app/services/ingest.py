from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.db.models import Item
from app.services import embed, extract, stt, vision
from app.services.storage import save_bytes

logger = logging.getLogger(__name__)


@dataclass
class PendingPayload:
    source_type: str
    telegram_message_id: int | None = None
    forward_from: str | None = None
    text: str | None = None
    caption: str | None = None
    file_bytes: bytes | None = None
    file_ext: str | None = None
    mime_type: str | None = None
    query_text: str | None = None
    preview: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


def _pdf_text(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages[:20]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception as exc:
        logger.warning("PDF text extract failed: %s", exc)
        return ""


def _pdf_first_page_image(path: Path) -> Path | None:
    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(path), first_page=1, last_page=1, dpi=150)
        if not images:
            return None
        out = path.with_suffix(".preview.jpg")
        images[0].save(out, "JPEG")
        return out
    except Exception as exc:
        logger.warning("PDF to image failed: %s", exc)
        return None


async def ingest_payload(session: AsyncSession, payload: PendingPayload) -> Item:
    file_path: Optional[str] = None
    mime_type = payload.mime_type
    raw_text = (payload.text or "").strip()
    caption = (payload.caption or "").strip()

    if payload.file_bytes and payload.file_ext:
        file_path = await save_bytes(payload.file_bytes, payload.file_ext)
        path = Path(file_path)

        if payload.source_type == "voice":
            transcript = await stt.transcribe_audio(path)
            raw_text = "\n".join(x for x in [caption, transcript] if x).strip()
        elif payload.source_type in {"photo", "image"}:
            described = await vision.describe_image(path, caption=caption or None)
            raw_text = "\n".join(x for x in [caption, described] if x).strip()
        elif payload.source_type == "document":
            if path.suffix.lower() == ".pdf":
                pdf_text = _pdf_text(path)
                if len(pdf_text) < 40:
                    preview = _pdf_first_page_image(path)
                    if preview:
                        described = await vision.describe_image(preview, caption=caption or None)
                        pdf_text = described
                raw_text = "\n".join(x for x in [caption, pdf_text] if x).strip()
            elif mime_type and mime_type.startswith("image/"):
                described = await vision.describe_image(path, caption=caption or None)
                raw_text = "\n".join(x for x in [caption, described] if x).strip()
            else:
                # binary/other docs: keep caption + filename hint
                raw_text = "\n".join(
                    x for x in [caption, f"Файл: {path.name}", raw_text] if x
                ).strip()
        else:
            if caption:
                raw_text = "\n".join(x for x in [caption, raw_text] if x).strip()

    if not raw_text and caption:
        raw_text = caption
    if not raw_text:
        raw_text = f"Сообщение типа {payload.source_type} без текста"

    fields = await extract.extract_fields(raw_text, source_hint=payload.source_type)
    if fields.get("event_date") is None:
        fields["event_date"] = date.today()

    embed_input = embed.build_embed_input(fields["title"], fields["summary"], raw_text)
    vector = await embed.embed_text(embed_input)

    item = await repository.create_item(
        session,
        source_type=payload.source_type,
        telegram_message_id=payload.telegram_message_id,
        forward_from=payload.forward_from,
        file_path=file_path,
        mime_type=mime_type,
        raw_text=raw_text,
        title=fields["title"],
        summary=fields["summary"],
        event_date=fields["event_date"],
        amount=fields["amount"],
        currency=fields["currency"],
        category=fields["category"],
        tags=fields["tags"],
        entities=fields["entities"],
        embedding=vector,
    )
    return item
