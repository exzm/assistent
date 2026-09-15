from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.repository import (
    build_similarity_query,
    create_item,
    get_item,
    list_recent,
    search_similar,
)


def test_build_similarity_query_filters():
    sql, params = build_similarity_query(
        event_date_from=date(2024, 1, 1),
        event_date_to=date(2024, 12, 31),
        min_amount=Decimal("1"),
        max_amount=Decimal("9"),
        category="finance",
    )
    assert "event_date >=" in sql
    assert params["category"] == "finance"


@pytest.mark.asyncio
async def test_repository_crud_and_search():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock(return_value="item")
    session.execute = AsyncMock()

    item = await create_item(session, title="t", source_type="text")
    assert item is not None
    assert session.add.called
    assert await get_item(session, 1) == "item"

    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a"]
    session.execute = AsyncMock(return_value=result)
    assert await list_recent(session) == ["a"]

    # empty search
    empty = MagicMock()
    empty.fetchall.return_value = []
    session.execute = AsyncMock(return_value=empty)
    assert await search_similar(session, [0.1, 0.2]) == []

    # ordered search
    ids_result = MagicMock()
    ids_result.fetchall.return_value = [(2,), (1,)]
    items_result = MagicMock()
    item1 = MagicMock(id=1)
    item2 = MagicMock(id=2)
    items_result.scalars.return_value.all.return_value = [item1, item2]
    session.execute = AsyncMock(side_effect=[ids_result, items_result])
    found = await search_similar(
        session,
        [0.1, 0.2],
        event_date_from=date(2024, 1, 1),
        category="note",
    )
    assert [i.id for i in found] == [2, 1]
