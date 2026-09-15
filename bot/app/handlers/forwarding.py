from __future__ import annotations

from aiogram.types import Message


def format_user_name(first_name: str | None, last_name: str | None, username: str | None) -> str:
    name = " ".join(part for part in (first_name, last_name) if part)
    if username:
        return f"{name} (@{username})" if name else f"@{username}"
    return name or "unknown"


def forward_from_message(message: Message) -> str | None:
    if message.forward_from:
        user = message.forward_from
        return format_user_name(user.first_name, user.last_name, user.username)
    if message.forward_from_chat:
        chat = message.forward_from_chat
        return chat.title or str(chat.id)
    if message.forward_sender_name:
        return message.forward_sender_name

    origin = getattr(message, "forward_origin", None)
    if origin is None:
        return None

    sender_user = getattr(origin, "sender_user", None)
    if sender_user is not None:
        return format_user_name(sender_user.first_name, sender_user.last_name, sender_user.username)

    chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
    if chat is not None:
        return getattr(chat, "title", None) or str(getattr(chat, "id", "forward"))

    sender_name = getattr(origin, "sender_user_name", None)
    if sender_name:
        return sender_name
    return None


def is_forward_message(message: Message) -> bool:
    return bool(
        message.forward_date
        or message.forward_from
        or message.forward_from_chat
        or message.forward_sender_name
        or getattr(message, "forward_origin", None)
    )


def resolve_source_type(message: Message, base: str) -> str:
    return "forward" if is_forward_message(message) else base
