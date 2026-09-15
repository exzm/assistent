from __future__ import annotations

TG_LIMIT = 4000


def clip_telegram(text: str, limit: int = TG_LIMIT) -> str:
    """Trim text to Telegram message limits."""
    value = text or ""
    if len(value) <= limit:
        return value
    marker = "\n…(truncated)"
    keep = max(0, limit - len(marker))
    return value[:keep] + marker


def join_nonempty(*parts: str | None, sep: str = "\n") -> str:
    return sep.join(part for part in parts if part)
