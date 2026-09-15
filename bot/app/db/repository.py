from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item
from app.utils.vectors import vector_literal


async def create_item(session: AsyncSession, **kwargs: Any) -> Item:
    item = Item(**kwargs)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_item(session: AsyncSession, item_id: int) -> Item | None:
    return await session.get(Item, item_id)


async def list_recent(session: AsyncSession, limit: int = 10) -> Sequence[Item]:
    result = await session.execute(select(Item).order_by(Item.created_at.desc()).limit(limit))
    return result.scalars().all()


def build_similarity_query(
    *,
    event_date_from: date | None = None,
    event_date_to: date | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    category: str | None = None,
) -> tuple[str, dict[str, Any]]:
    clauses = ["embedding IS NOT NULL"]
    params: dict[str, Any] = {}

    if event_date_from is not None:
        clauses.append("event_date >= :date_from")
        params["date_from"] = event_date_from
    if event_date_to is not None:
        clauses.append("event_date <= :date_to")
        params["date_to"] = event_date_to
    if min_amount is not None:
        clauses.append("amount >= :min_amount")
        params["min_amount"] = min_amount
    if max_amount is not None:
        clauses.append("amount <= :max_amount")
        params["max_amount"] = max_amount
    if category:
        clauses.append("category = :category")
        params["category"] = category

    where = " AND ".join(clauses)
    sql = f"""
        SELECT id
        FROM items
        WHERE {where}
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :top_k
    """
    return sql, params


async def search_similar(
    session: AsyncSession,
    embedding: list[float],
    top_k: int = 5,
    event_date_from: date | None = None,
    event_date_to: date | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    category: str | None = None,
) -> Sequence[Item]:
    sql, params = build_similarity_query(
        event_date_from=event_date_from,
        event_date_to=event_date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        category=category,
    )
    params = {
        **params,
        "emb": vector_literal(embedding),
        "top_k": top_k,
    }
    result = await session.execute(text(sql), params)
    ids = [row[0] for row in result.fetchall()]
    if not ids:
        return []

    items_result = await session.execute(select(Item).where(Item.id.in_(ids)))
    items = {item.id: item for item in items_result.scalars().all()}
    return [items[item_id] for item_id in ids if item_id in items]
