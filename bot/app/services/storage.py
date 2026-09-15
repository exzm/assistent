from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from app.config import get_settings


def ensure_files_dir() -> Path:
    root = Path(get_settings().files_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_storage_path(extension: str) -> Path:
    now = datetime.utcnow()
    folder = ensure_files_dir() / f"{now.year:04d}" / f"{now.month:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    ext = extension.lstrip(".") or "bin"
    return folder / f"{uuid.uuid4().hex}.{ext}"


async def save_bytes(data: bytes, extension: str) -> str:
    path = build_storage_path(extension)
    path.write_bytes(data)
    return str(path)
