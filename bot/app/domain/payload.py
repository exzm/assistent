from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PendingPayload:
    """In-memory representation of a message waiting for Save/Ask."""

    source_type: str
    telegram_message_id: int | None = None
    forward_from: str | None = None
    text: str | None = None
    caption: str | None = None
    file_bytes: bytes | None = None
    file_ext: str | None = None
    mime_type: str | None = None
    query_text: str | None = None
    preview: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
