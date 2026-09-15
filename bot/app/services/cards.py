from __future__ import annotations

from decimal import Decimal

from app.db.models import Item


def format_item_card(item: Item) -> str:
    lines = [f"#{item.id} · {item.title or 'Без названия'}"]
    if item.event_date:
        lines.append(f"Дата: {item.event_date.isoformat()}")
    if item.amount is not None:
        currency = item.currency or ""
        amount = item.amount if isinstance(item.amount, Decimal) else Decimal(str(item.amount))
        lines.append(f"Сумма: {amount} {currency}".strip())
    if item.category:
        lines.append(f"Категория: {item.category}")
    if item.tags:
        lines.append("Теги: " + ", ".join(item.tags[:8]))
    if item.summary:
        lines.append(item.summary)
    return "\n".join(lines)


def format_cards(items: list[Item], limit: int = 3) -> str:
    if not items:
        return "Источники не найдены."
    return "\n\n".join(format_item_card(item) for item in items[:limit])
