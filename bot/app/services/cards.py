from __future__ import annotations

from decimal import Decimal
from typing import Protocol


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
    lines = [f"#{item.id} · {item.title or 'Untitled'}"]
    if item.event_date is not None:
        lines.append(f"Date: {item.event_date.isoformat()}")  # type: ignore[union-attr]
    if item.amount is not None:
        currency = item.currency or ""
        amount = item.amount if isinstance(item.amount, Decimal) else Decimal(str(item.amount))
        lines.append(f"Amount: {amount} {currency}".strip())
    if item.category:
        lines.append(f"Category: {item.category}")
    if item.tags:
        lines.append("Tags: " + ", ".join(item.tags[:8]))
    if item.summary:
        lines.append(item.summary)
    return "\n".join(lines)


def format_cards(items: list[CardItem], limit: int = 3) -> str:
    if not items:
        return "No sources found."
    return "\n\n".join(format_item_card(item) for item in items[:limit])
