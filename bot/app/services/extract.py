from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings, get_settings
from app.services.proxyapi import get_openai_client
from app.utils.parsing import (
    extract_json_object,
    normalize_category,
    parse_amount,
    parse_date,
)
from app.utils.text import join_nonempty

EXTRACT_SCHEMA_HINT = """
Return ONLY valid JSON without markdown:
{
  "title": "short title",
  "summary": "1-2 sentences",
  "event_date": "YYYY-MM-DD or null",
  "amount": number or null,
  "currency": "RUB/USD/... or null",
  "category": "finance|auto_service|contract|health|note|other",
  "tags": ["tag1", "tag2"],
  "entities": {"key": "value"}
}
Categories: finance — bills/payments; auto_service — car maintenance; contract — contracts;
health — medical; note — notes; other — everything else.
"""


def normalize_extracted_fields(data: dict[str, Any], raw_text: str) -> dict[str, Any]:
    """Normalize LLM JSON into a stable ingest payload."""
    tags = data.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tags = [str(tag).strip() for tag in tags if str(tag).strip()][:12]

    entities = data.get("entities") or {}
    if not isinstance(entities, dict):
        entities = {}

    fallback_title = raw_text[:80].strip() if raw_text else "Untitled"
    title = (data.get("title") or "").strip() or fallback_title
    summary = (data.get("summary") or "").strip() or title
    currency = data.get("currency")

    return {
        "title": title[:200],
        "summary": summary[:1000],
        "event_date": parse_date(data.get("event_date")),
        "amount": parse_amount(data.get("amount")),
        "currency": str(currency).upper() if currency else None,
        "category": normalize_category(data.get("category")),
        "tags": tags,
        "entities": entities,
    }


async def extract_fields(
    raw_text: str,
    source_hint: str = "",
    *,
    client: AsyncOpenAI | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    openai_client = client or get_openai_client(cfg)
    prompt = (
        f"Source: {source_hint or 'unknown'}\n"
        f"Text:\n{raw_text[:12000]}\n\n"
        f"{EXTRACT_SCHEMA_HINT}"
    )
    response = await openai_client.chat.completions.create(
        model=cfg.model_extract,
        messages=[
            {
                "role": "system",
                "content": "You extract structured facts from personal notes and documents.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    return normalize_extracted_fields(extract_json_object(content), raw_text)


def build_fallback_raw_text(source_type: str, caption: str = "", filename: str = "") -> str:
    return join_nonempty(caption, f"File: {filename}" if filename else None) or (
        f"{source_type} message without text"
    )


def resolve_document_raw_text(
    *,
    path: Path,
    mime_type: str | None,
    caption: str,
    existing_text: str,
    pdf_text: str,
    vision_text: str | None,
) -> str:
    if path.suffix.lower() == ".pdf":
        body = pdf_text if len(pdf_text) >= 40 else (vision_text or pdf_text)
        return join_nonempty(caption, body) or build_fallback_raw_text("document", caption, path.name)
    if mime_type and mime_type.startswith("image/"):
        return join_nonempty(caption, vision_text) or build_fallback_raw_text("document", caption, path.name)
    return join_nonempty(caption, f"File: {path.name}", existing_text) or build_fallback_raw_text(
        "document", caption, path.name
    )
