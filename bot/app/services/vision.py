from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from app.config import get_settings
from app.services.proxyapi import get_openai_client

VISION_PROMPT = """Ты извлекаешь текст и факты из изображения документа/счета/заметки.
Верни обычный текст на русском:
1) Полный распознанный текст (OCR)
2) Кратко: что это за документ
Не выдумывай то, чего нет на изображении."""


def _data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


async def describe_image(file_path: str | Path, caption: str | None = None) -> str:
    settings = get_settings()
    client = get_openai_client()
    path = Path(file_path)
    user_text = VISION_PROMPT
    if caption:
        user_text += f"\n\nПодпись пользователя: {caption}"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": _data_url(path)}},
            ],
        }
    ]

    try:
        response = await client.chat.completions.create(
            model=settings.model_vision,
            messages=messages,
            temperature=0.1,
        )
    except Exception:
        response = await client.chat.completions.create(
            model=settings.model_vision_fallback,
            messages=messages,
            temperature=0.1,
        )

    return (response.choices[0].message.content or "").strip()
