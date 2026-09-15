from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings, get_settings


def ensure_files_dir(settings: Settings | None = None) -> Path:
    root = Path((settings or get_settings()).files_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_storage_path(
    extension: str,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
    uuid_factory=uuid.uuid4,
) -> Path:
    current = now or datetime.now(UTC)
    folder = ensure_files_dir(settings) / f"{current.year:04d}" / f"{current.month:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    ext = extension.lstrip(".") or "bin"
    return folder / f"{uuid_factory().hex}.{ext}"


async def save_bytes(
    data: bytes,
    extension: str,
    *,
    settings: Settings | None = None,
) -> str:
    path = build_storage_path(extension, settings=settings)
    path.write_bytes(data)
    return str(path)
