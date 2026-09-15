from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.db.models import Item
from app.domain.payload import PendingPayload
from app.services import embed, extract, stt, vision
from app.services.storage import save_bytes
from app.utils.text import join_nonempty

logger = logging.getLogger(__name__)


def extract_pdf_text(path: Path, *, max_pages: int = 20) -> str:
    try:
        reader = PdfReader(str(path))
        parts = [(page.extract_text() or "") for page in reader.pages[:max_pages]]
        return "\n".join(parts).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF text extract failed: %s", exc)
        return ""


def render_pdf_preview(path: Path) -> Path | None:
    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(path), first_page=1, last_page=1, dpi=150)
        if not images:
            return None
        out = path.with_suffix(".preview.jpg")
        images[0].save(out, "JPEG")
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF to image failed: %s", exc)
        return None


async def resolve_raw_text(payload: PendingPayload, path: Path | None) -> str:
    caption = (payload.caption or "").strip()
    raw_text = (payload.text or "").strip()

    if path is None:
        return raw_text or caption or f"{payload.source_type} message without text"

    if payload.source_type == "voice":
        transcript = await stt.transcribe_audio(path)
        return join_nonempty(caption, transcript) or f"{payload.source_type} message without text"

    if payload.source_type in {"photo", "image"}:
        described = await vision.describe_image(path, caption=caption or None)
        return join_nonempty(caption, described) or f"{payload.source_type} message without text"

    if payload.source_type == "document":
        if path.suffix.lower() == ".pdf":
            pdf_text = extract_pdf_text(path)
            vision_text = None
            if len(pdf_text) < 40:
                preview = render_pdf_preview(path)
                if preview is not None:
                    vision_text = await vision.describe_image(preview, caption=caption or None)
            return extract.resolve_document_raw_text(
                path=path,
                mime_type=payload.mime_type,
                caption=caption,
                existing_text=raw_text,
                pdf_text=pdf_text,
                vision_text=vision_text,
            )
        if payload.mime_type and payload.mime_type.startswith("image/"):
            described = await vision.describe_image(path, caption=caption or None)
            return extract.resolve_document_raw_text(
                path=path,
                mime_type=payload.mime_type,
                caption=caption,
                existing_text=raw_text,
                pdf_text="",
                vision_text=described,
            )
        return extract.resolve_document_raw_text(
            path=path,
            mime_type=payload.mime_type,
            caption=caption,
            existing_text=raw_text,
            pdf_text="",
            vision_text=None,
        )

    return join_nonempty(caption, raw_text) or f"{payload.source_type} message without text"


async def ingest_payload(session: AsyncSession, payload: PendingPayload) -> Item:
    file_path: str | None = None
    path: Path | None = None

    if payload.file_bytes and payload.file_ext:
        file_path = await save_bytes(payload.file_bytes, payload.file_ext)
        path = Path(file_path)

    raw_text = await resolve_raw_text(payload, path)
    fields = await extract.extract_fields(raw_text, source_hint=payload.source_type)
    if fields.get("event_date") is None:
        fields["event_date"] = date.today()

    vector = await embed.embed_text(
        embed.build_embed_input(fields["title"], fields["summary"], raw_text)
    )

    return await repository.create_item(
        session,
        source_type=payload.source_type,
        telegram_message_id=payload.telegram_message_id,
        forward_from=payload.forward_from,
        file_path=file_path,
        mime_type=payload.mime_type,
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
