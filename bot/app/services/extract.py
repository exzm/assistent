from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.config import get_settings
from app.services.proxyapi import get_openai_client

EXTRACT_SCHEMA_HINT = """
Верни ТОЛЬКО валидный JSON без markdown:
{
  "title": "краткий заголовок",
  "summary": "1-2 предложения",
  "event_date": "YYYY-MM-DD или null",
  "amount": число или null,
  "currency": "RUB/USD/... или null",
  "category": "finance|auto_service|contract|health|note|other",
  "tags": ["тег1", "тег2"],
  "entities": {"ключ": "значение"}
}
Категории: finance — счета/оплаты; auto_service — ТО/масло/авто; contract — договоры;
health — медицина; note — заметки; other — прочее.
"""


def _parse_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ".").replace(" ", ""))
    except (InvalidOperation, ValueError):
        return None


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    return {}


async def extract_fields(raw_text: str, source_hint: str = "") -> dict[str, Any]:
    settings = get_settings()
    client = get_openai_client()
    prompt = (
        f"Источник: {source_hint or 'unknown'}\n"
        f"Текст:\n{raw_text[:12000]}\n\n"
        f"{EXTRACT_SCHEMA_HINT}"
    )
    response = await client.chat.completions.create(
        model=settings.model_extract,
        messages=[
            {"role": "system", "content": "Ты извлекаешь структурированные факты из личных заметок и документов."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    data = _extract_json(content)

    tags = data.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip() for t in tags if str(t).strip()][:12]

    entities = data.get("entities") or {}
    if not isinstance(entities, dict):
        entities = {}

    title = (data.get("title") or "").strip() or (raw_text[:80].strip() if raw_text else "Без названия")
    summary = (data.get("summary") or "").strip() or title
    category = (data.get("category") or "other").strip()
    if category not in {"finance", "auto_service", "contract", "health", "note", "other"}:
        category = "other"

    return {
        "title": title[:200],
        "summary": summary[:1000],
        "event_date": _parse_date(data.get("event_date")),
        "amount": _parse_amount(data.get("amount")),
        "currency": (str(data.get("currency")).upper() if data.get("currency") else None),
        "category": category,
        "tags": tags,
        "entities": entities,
    }
