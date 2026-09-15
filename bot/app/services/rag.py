from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import repository
from app.db.models import Item
from app.services import embed
from app.services.cards import format_cards
from app.services.proxyapi import get_openai_client
from app.utils.parsing import (
    extract_json_object,
    normalize_optional_category,
    parse_amount,
    parse_date,
)
from app.utils.text import markdown_lite_to_html

INTENT_PROMPT = """Extract search filters from the user question. Return ONLY JSON:
{
  "rewritten_query": "improved search query",
  "event_date_from": "YYYY-MM-DD or null",
  "event_date_to": "YYYY-MM-DD or null",
  "min_amount": number or null,
  "max_amount": number or null,
  "category": "finance|auto_service|contract|health|note|other|null"
}
"""

EMPTY_ANSWER = (
    "No matching records yet. Save a note or document and ask again."
)


def normalize_intent(data: dict[str, Any], question: str) -> dict[str, Any]:
    return {
        "rewritten_query": (data.get("rewritten_query") or question).strip(),
        "event_date_from": parse_date(data.get("event_date_from"), formats=("%Y-%m-%d",)),
        "event_date_to": parse_date(data.get("event_date_to"), formats=("%Y-%m-%d",)),
        "min_amount": parse_amount(data.get("min_amount")),
        "max_amount": parse_amount(data.get("max_amount")),
        "category": normalize_optional_category(data.get("category")),
    }


def build_items_context(items: list[Item]) -> str:
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


def compose_answer(answer: str, items: list[Item], *, card_limit: int = 3) -> str:
    cards = format_cards(items, limit=card_limit)
    body = markdown_lite_to_html(answer)
    return f"{body}\n\n—\n<b>Карточки:</b>\n{cards}"


async def parse_intent(
    question: str,
    *,
    client: AsyncOpenAI | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    openai_client = client or get_openai_client(cfg)
    response = await openai_client.chat.completions.create(
        model=cfg.model_chat,
        messages=[
            {"role": "system", "content": INTENT_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return normalize_intent(
        extract_json_object(response.choices[0].message.content or "{}"),
        question,
    )


async def answer_question(
    session: AsyncSession,
    question: str,
    *,
    client: AsyncOpenAI | None = None,
    settings: Settings | None = None,
) -> tuple[str, list[Item]]:
    cfg = settings or get_settings()
    openai_client = client or get_openai_client(cfg)
    intent = await parse_intent(question, client=openai_client, settings=cfg)
    query = intent["rewritten_query"]
    vector = await embed.embed_text(query, client=openai_client, settings=cfg)

    items = list(
        await repository.search_similar(
            session,
            embedding=vector,
            top_k=cfg.rag_top_k,
            event_date_from=intent["event_date_from"],
            event_date_to=intent["event_date_to"],
            min_amount=intent["min_amount"],
            max_amount=intent["max_amount"],
            category=intent["category"],
        )
    )
    if not items:
        items = list(
            await repository.search_similar(
                session,
                embedding=vector,
                top_k=cfg.rag_top_k,
            )
        )
    if not items:
        return EMPTY_ANSWER, []

    response = await openai_client.chat.completions.create(
        model=cfg.model_chat,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a personal assistant over the user's archive. "
                    "Answer only from the provided records. Mention #id and dates. "
                    "If data is insufficient, say so. Be concise."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nRecords:\n{build_items_context(items)}",
            },
        ],
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()
    return compose_answer(answer, items), items
