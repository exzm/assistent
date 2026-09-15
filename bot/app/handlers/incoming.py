from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.keyboards import pending_action_keyboard
from app.services.download import download_telegram_file
from app.services.ingest import PendingPayload
from app.services.pending import put_pending

router = Router(name="incoming")


def _forward_from(message: Message) -> str | None:
    if message.forward_from:
        user = message.forward_from
        name = " ".join(x for x in [user.first_name, user.last_name] if x)
        return f"{name} (@{user.username})" if user.username else name
    if message.forward_from_chat:
        chat = message.forward_from_chat
        return chat.title or str(chat.id)
    if message.forward_sender_name:
        return message.forward_sender_name
    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        sender_user = getattr(origin, "sender_user", None)
        if sender_user is not None:
            name = " ".join(x for x in [sender_user.first_name, sender_user.last_name] if x)
            return f"{name} (@{sender_user.username})" if sender_user.username else name
        chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
        if chat is not None:
            return getattr(chat, "title", None) or str(getattr(chat, "id", "forward"))
        sender_name = getattr(origin, "sender_user_name", None)
        if sender_name:
            return sender_name
    return None


def _is_forward(message: Message) -> bool:
    return bool(
        message.forward_date
        or message.forward_from
        or message.forward_from_chat
        or message.forward_sender_name
        or getattr(message, "forward_origin", None)
    )


def _source_type(message: Message, base: str) -> str:
    if _is_forward(message):
        return "forward"
    return base


async def _offer(message: Message, payload: PendingPayload) -> None:
    pending_id = put_pending(payload)
    text = payload.preview or "Сообщение получено."
    await message.answer(
        f"{text}\n\nЧто сделать?",
        reply_markup=pending_action_keyboard(pending_id),
    )


@router.message(F.voice)
async def on_voice(message: Message) -> None:
    content = await download_telegram_file(message, message.voice.file_id)
    payload = PendingPayload(
        source_type=_source_type(message, "voice"),
        telegram_message_id=message.message_id,
        forward_from=_forward_from(message),
        caption=message.caption,
        file_bytes=content,
        file_ext="ogg",
        mime_type=message.voice.mime_type or "audio/ogg",
        query_text=message.caption,
        preview="Голосовое получено. При сохранении будет расшифровка.",
    )
    await _offer(message, payload)


@router.message(F.audio)
async def on_audio(message: Message) -> None:
    content = await download_telegram_file(message, message.audio.file_id)
    ext = "mp3"
    if message.audio.file_name and "." in message.audio.file_name:
        ext = message.audio.file_name.rsplit(".", 1)[-1]
    payload = PendingPayload(
        source_type=_source_type(message, "voice"),
        telegram_message_id=message.message_id,
        forward_from=_forward_from(message),
        caption=message.caption,
        file_bytes=content,
        file_ext=ext,
        mime_type=message.audio.mime_type or "audio/mpeg",
        query_text=message.caption,
        preview=f"Аудио получено ({message.audio.file_name or 'file'}).",
    )
    await _offer(message, payload)


@router.message(F.photo)
async def on_photo(message: Message) -> None:
    photo = message.photo[-1]
    content = await download_telegram_file(message, photo.file_id)
    caption = message.caption or ""
    preview = "Фото получено."
    if caption:
        preview += f"\nПодпись: {caption[:300]}"
    payload = PendingPayload(
        source_type=_source_type(message, "photo"),
        telegram_message_id=message.message_id,
        forward_from=_forward_from(message),
        caption=caption or None,
        file_bytes=content,
        file_ext="jpg",
        mime_type="image/jpeg",
        query_text=caption or None,
        preview=preview,
    )
    await _offer(message, payload)


@router.message(F.document)
async def on_document(message: Message) -> None:
    doc = message.document
    content = await download_telegram_file(message, doc.file_id)
    name = doc.file_name or "file.bin"
    ext = name.rsplit(".", 1)[-1] if "." in name else "bin"
    mime = doc.mime_type or "application/octet-stream"
    source = "photo" if mime.startswith("image/") else "document"
    caption = message.caption or ""
    preview = f"Документ получен: {name}"
    if caption:
        preview += f"\nПодпись: {caption[:300]}"
    payload = PendingPayload(
        source_type=_source_type(message, source),
        telegram_message_id=message.message_id,
        forward_from=_forward_from(message),
        caption=caption or None,
        file_bytes=content,
        file_ext=ext,
        mime_type=mime,
        query_text=caption or name,
        preview=preview,
    )
    await _offer(message, payload)


@router.message(F.text)
async def on_text(message: Message) -> None:
    if message.text and message.text.startswith("/"):
        return
    text = (message.text or "").strip()
    if not text:
        return
    preview = f"Текст:\n{text[:500]}"
    if len(text) > 500:
        preview += "…"
    payload = PendingPayload(
        source_type=_source_type(message, "text"),
        telegram_message_id=message.message_id,
        forward_from=_forward_from(message),
        text=text,
        query_text=text,
        preview=preview,
    )
    await _offer(message, payload)
