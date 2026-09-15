from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from openai import AsyncOpenAI

from app.config import Settings, get_settings
from app.services.proxyapi import get_openai_client

VISION_PROMPT = """Extract text and facts from an image of a document/receipt/note.
Return plain text:
1) Full OCR text
2) Short description of the document type
Do not invent details that are not present in the image."""


def image_to_data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_vision_messages(path: Path, caption: str | None = None) -> list[dict]:
    user_text = VISION_PROMPT
    if caption:
        user_text += f"\n\nUser caption: {caption}"
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": image_to_data_url(path)}},
            ],
        }
    ]


async def describe_image(
    file_path: str | Path,
    caption: str | None = None,
    *,
    client: AsyncOpenAI | None = None,
    settings: Settings | None = None,
) -> str:
    cfg = settings or get_settings()
    openai_client = client or get_openai_client(cfg)
    path = Path(file_path)
    messages = build_vision_messages(path, caption=caption)

    try:
        response = await openai_client.chat.completions.create(
            model=cfg.model_vision,
            messages=messages,
            temperature=0.1,
        )
    except Exception:
        response = await openai_client.chat.completions.create(
            model=cfg.model_vision_fallback,
            messages=messages,
            temperature=0.1,
        )

    return (response.choices[0].message.content or "").strip()
