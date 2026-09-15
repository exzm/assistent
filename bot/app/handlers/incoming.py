from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.domain.payload import PendingPayload
from app.handlers.forwarding import forward_from_message, resolve_source_type
from app.keyboards import pending_action_keyboard
from app.services.download import download_telegram_file
from app.services.pending import put_pending

router = Router(name="incoming")


async def offer_pending(message: Message, payload: PendingPayload) -> str:
    pending_id = put_pending(payload)
    text = payload.preview or "Message received."
    await message.answer(
        f"{text}\n\nWhat should I do?",
        reply_markup=pending_action_keyboard(pending_id),
    )
    return pending_id


@router.message(F.voice)
async def on_voice(message: Message) -> None:
    assert message.voice is not None
    content = await download_telegram_file(message, message.voice.file_id)
    payload = PendingPayload(
        source_type=resolve_source_type(message, "voice"),
        telegram_message_id=message.message_id,
        forward_from=forward_from_message(message),
        caption=message.caption,
        file_bytes=content,
        file_ext="ogg",
        mime_type=message.voice.mime_type or "audio/ogg",
        query_text=message.caption,
        preview="Voice message received. It will be transcribed on save.",
    )
    await offer_pending(message, payload)


@router.message(F.audio)
async def on_audio(message: Message) -> None:
    assert message.audio is not None
    content = await download_telegram_file(message, message.audio.file_id)
    ext = "mp3"
    if message.audio.file_name and "." in message.audio.file_name:
        ext = message.audio.file_name.rsplit(".", 1)[-1]
    payload = PendingPayload(
        source_type=resolve_source_type(message, "voice"),
        telegram_message_id=message.message_id,
        forward_from=forward_from_message(message),
        caption=message.caption,
        file_bytes=content,
        file_ext=ext,
        mime_type=message.audio.mime_type or "audio/mpeg",
        query_text=message.caption,
        preview=f"Audio received ({message.audio.file_name or 'file'}).",
    )
    await offer_pending(message, payload)


@router.message(F.photo)
async def on_photo(message: Message) -> None:
    assert message.photo
    photo = message.photo[-1]
    content = await download_telegram_file(message, photo.file_id)
    caption = message.caption or ""
    preview = "Photo received."
    if caption:
        preview += f"\nCaption: {caption[:300]}"
    payload = PendingPayload(
        source_type=resolve_source_type(message, "photo"),
        telegram_message_id=message.message_id,
        forward_from=forward_from_message(message),
        caption=caption or None,
        file_bytes=content,
        file_ext="jpg",
        mime_type="image/jpeg",
        query_text=caption or None,
        preview=preview,
    )
    await offer_pending(message, payload)


@router.message(F.document)
async def on_document(message: Message) -> None:
    assert message.document is not None
    doc = message.document
    content = await download_telegram_file(message, doc.file_id)
    name = doc.file_name or "file.bin"
    ext = name.rsplit(".", 1)[-1] if "." in name else "bin"
    mime = doc.mime_type or "application/octet-stream"
    source = "photo" if mime.startswith("image/") else "document"
    caption = message.caption or ""
    preview = f"Document received: {name}"
    if caption:
        preview += f"\nCaption: {caption[:300]}"
    payload = PendingPayload(
        source_type=resolve_source_type(message, source),
        telegram_message_id=message.message_id,
        forward_from=forward_from_message(message),
        caption=caption or None,
        file_bytes=content,
        file_ext=ext,
        mime_type=mime,
        query_text=caption or name,
        preview=preview,
    )
    await offer_pending(message, payload)


@router.message(F.text)
async def on_text(message: Message) -> None:
    if message.text and message.text.startswith("/"):
        return
    text = (message.text or "").strip()
    if not text:
        return
    preview = f"Text:\n{text[:500]}"
    if len(text) > 500:
        preview += "…"
    payload = PendingPayload(
        source_type=resolve_source_type(message, "text"),
        telegram_message_id=message.message_id,
        forward_from=forward_from_message(message),
        text=text,
        query_text=text,
        preview=preview,
    )
    await offer_pending(message, payload)
