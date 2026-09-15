from __future__ import annotations

import html
import re

TG_LIMIT = 4000

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_CODE_RE = re.compile(r"`([^`]+)`")


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


def escape_html(text: str) -> str:
    return html.escape(text or "", quote=False)


def markdown_lite_to_html(text: str) -> str:
    """Convert a small Markdown subset to Telegram HTML."""
    escaped = escape_html(text or "")
    escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
    escaped = _ITALIC_RE.sub(r"<i>\1</i>", escaped)
    escaped = _CODE_RE.sub(r"<code>\1</code>", escaped)
    return escaped


def prepare_telegram_html(text: str, *, limit: int = TG_LIMIT) -> str:
    """Escape/convert formatting and clip for Telegram HTML messages."""
    return clip_telegram(markdown_lite_to_html(text), limit=limit)
