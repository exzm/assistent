
import pytest

from app.domain.payload import PendingPayload
from app.services.pending import (
    PendingStore,
    get_pending,
    get_pending_store,
    pop_pending,
    put_pending,
    reset_pending_store,
)


def test_pending_store_ttl_and_ops():
    clock = {"now": 100.0}
    store = PendingStore(ttl_seconds=10, clock=lambda: clock["now"], id_factory=lambda: "abc123")
    payload = PendingPayload(source_type="text", text="hi")
    assert store.put(payload) == "abc123"
    assert store.get("abc123") is payload
    clock["now"] = 200.0
    assert store.get("abc123") is None
    store.put(payload)
    assert store.pop("abc123") is payload
    assert store.pop("missing") is None
    store.put(payload)
    store.clear()
    assert store.get("abc123") is None


def test_pending_store_invalid_ttl():
    with pytest.raises(ValueError):
        PendingStore(ttl_seconds=0)


def test_default_pending_store_wrappers():
    reset_pending_store()
    payload = PendingPayload(source_type="text", text="x")
    pending_id = put_pending(payload)
    assert get_pending(pending_id) is payload
    assert pop_pending(pending_id) is payload
    assert get_pending_store() is not None
