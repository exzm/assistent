TG_LIMIT = 4000


def clip_telegram(text: str, limit: int = TG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n…(обрезано)"
