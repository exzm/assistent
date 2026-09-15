from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from app.domain.payload import PendingPayload


class PendingStore:
    """TTL-backed in-memory store for pending Save/Ask actions."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 3600,
        clock: Callable[[], float] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl_seconds = ttl_seconds
        self._clock = clock or time.time
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex[:12])
        self._store: dict[str, tuple[float, PendingPayload]] = {}

    def put(self, payload: PendingPayload) -> str:
        pending_id = self._id_factory()
        self._store[pending_id] = (self._clock(), payload)
        self.cleanup()
        return pending_id

    def pop(self, pending_id: str) -> PendingPayload | None:
        self.cleanup()
        entry = self._store.pop(pending_id, None)
        return None if entry is None else entry[1]

    def get(self, pending_id: str) -> PendingPayload | None:
        self.cleanup()
        entry = self._store.get(pending_id)
        return None if entry is None else entry[1]

    def cleanup(self) -> None:
        now = self._clock()
        expired = [key for key, (ts, _) in self._store.items() if now - ts > self._ttl_seconds]
        for key in expired:
            self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


_DEFAULT_STORE: PendingStore | None = None


def get_pending_store(ttl_seconds: int | None = None) -> PendingStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        from app.config import get_settings

        ttl = ttl_seconds if ttl_seconds is not None else get_settings().pending_ttl_seconds
        _DEFAULT_STORE = PendingStore(ttl_seconds=ttl)
    return _DEFAULT_STORE


def reset_pending_store() -> None:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is not None:
        _DEFAULT_STORE.clear()
    _DEFAULT_STORE = None


def put_pending(payload: PendingPayload) -> str:
    return get_pending_store().put(payload)


def pop_pending(pending_id: str) -> PendingPayload | None:
    return get_pending_store().pop(pending_id)


def get_pending(pending_id: str) -> PendingPayload | None:
    return get_pending_store().get(pending_id)
