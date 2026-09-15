from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import repository
from app.db.models import Item
from app.services import embed
from app.services.cards import format_cards
from app.services.proxyapi import get_openai_client

INTENT_PROMPT = """Из пользовательского вопроса извлеки фильтры поиска. Верни ТОЛЬКО JSON:
{
  "rewritten_query": "улучшенный поисковый запрос",
  "event_date_from": "YYYY-MM-DD или null",
  "event_date_to": "YYYY-MM-DD или null",
  "min_amount": число или null,
  "max_amount": число или null,
  "category": "finance|auto_service|contract|health|note|other|null"
}
"""


def _parse_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_amount(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
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


async def parse_intent(question: str) -> dict[str, Any]:
    settings = get_settings()
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.model_chat,
        messages=[
            {"role": "system", "content": INTENT_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    data = _extract_json(response.choices[0].message.content or "{}")
    category = data.get("category")
    if category not in {"finance", "auto_service", "contract", "health", "note", "other"}:
        category = None
    return {
        "rewritten_query": (data.get("rewritten_query") or question).strip(),
        "event_date_from": _parse_date(data.get("event_date_from")),
        "event_date_to": _parse_date(data.get("event_date_to")),
        "min_amount": _parse_amount(data.get("min_amount")),
        "max_amount": _parse_amount(data.get("max_amount")),
        "category": category,
    }


def _items_context(items: list[Item]) -> str:
    blocks: list[str] = []
    for item in items:
        blocks.append(
            "\n".join(
                [
                    f"ID: #{item.id}",
                    f"Title: {item.title}",
                    f"Date: {item.event_date}",
                    f"Amount: {item.amount} {item.currency or ''}".strip(),
                    f"Category: {item.category}",
                    f"Tags: {', '.join(item.tags or [])}",
                    f"Summary: {item.summary}",
                    f"Text: {(item.raw_text or '')[:1500]}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


async def answer_question(session: AsyncSession, question: str) -> tuple[str, list[Item]]:
    settings = get_settings()
    intent = await parse_intent(question)
    query = intent["rewritten_query"]
    vector = await embed.embed_text(query)
    items = list(
        await repository.search_similar(
            session,
            embedding=vector,
            top_k=settings.rag_top_k,
            event_date_from=intent["event_date_from"],
            event_date_to=intent["event_date_to"],
            min_amount=intent["min_amount"],
            max_amount=intent["max_amount"],
            category=intent["category"],
        )
    )

    if not items:
        # fallback without filters
        items = list(await repository.search_similar(session, embedding=vector, top_k=settings.rag_top_k))

    if not items:
        return "Пока нет подходящих записей в базе. Сохрани заметку или документ и спроси снова.", []

    client = get_openai_client()
    system = (
        "Ты личный ассистент по архиву заметок пользователя. "
        "Отвечай только на основе найденных записей. Указывай #id и даты. "
        "Если данных недостаточно — так и скажи. Отвечай кратко на русском."
    )
    user = f"Вопрос: {question}\n\nНайденные записи:\n{_items_context(items)}"
    response = await client.chat.completions.create(
        model=settings.model_chat,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    cards = format_cards(items, limit=3)
    full = f"{answer}\n\n—\nКарточки:\n{cards}"
    return full, items
