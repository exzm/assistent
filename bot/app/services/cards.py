from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from app.utils.text import escape_html


class CardItem(Protocol):
    id: int
    title: str | None
    event_date: object | None
    amount: object | None
    currency: str | None
    category: str | None
    tags: list[str] | None
    summary: str | None


def format_item_card(item: CardItem) -> str:
    title = escape_html(item.title or "Без названия")
    lines = [f"<b>#{item.id}</b> · {title}"]
    if item.event_date is not None:
        lines.append(f"Дата: {escape_html(item.event_date.isoformat())}")  # type: ignore[union-attr]
    if item.amount is not None:
        currency = item.currency or ""
        amount = item.amount if isinstance(item.amount, Decimal) else Decimal(str(item.amount))
        lines.append(f"Сумма: {escape_html(f'{amount} {currency}'.strip())}")
    if item.category:
        lines.append(f"Категория: {escape_html(item.category)}")
    if item.tags:
        lines.append("Теги: " + escape_html(", ".join(item.tags[:8])))
    if item.summary:
        lines.append(escape_html(item.summary))
    return "\n".join(lines)


def format_cards(items: list[CardItem], limit: int = 3) -> str:
    if not items:
        return "Источники не найдены."
    return "\n\n".join(format_item_card(item) for item in items[:limit])
