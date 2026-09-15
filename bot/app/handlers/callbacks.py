from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.payload import PendingPayload
from app.services.cards import format_item_card
from app.services.ingest import ingest_payload
from app.services.pending import pop_pending
from app.services.query_text import materialize_query_text
from app.services.rag import answer_question
from app.utils.text import clip_telegram

router = Router(name="callbacks")


def parse_action_data(data: str | None) -> tuple[str, str] | None:
    if not data:
        return None
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "act":
        return None
    return parts[1], parts[2]


async def edit_or_send(callback: CallbackQuery, text: str) -> None:
    if callback.message:
        await callback.message.edit_text(text)
    else:
        await callback.bot.send_message(callback.from_user.id, text)


async def handle_save(callback: CallbackQuery, session: AsyncSession, payload: PendingPayload) -> None:
    await edit_or_send(callback, "Saving…")
    try:
        item = await ingest_payload(session, payload)
        await edit_or_send(callback, clip_telegram("Saved.\n\n" + format_item_card(item)))
    except Exception as exc:  # noqa: BLE001
        await edit_or_send(callback, f"Failed to save: {exc}")


async def handle_ask(callback: CallbackQuery, session: AsyncSession, payload: PendingPayload) -> None:
    await edit_or_send(callback, "Preparing question…")
    try:
        question = await materialize_query_text(payload)
    except Exception as exc:  # noqa: BLE001
        await edit_or_send(callback, f"Failed to prepare question: {exc}")
        return

    if not question:
        await edit_or_send(
            callback,
            "Could not extract a question. Send text or use /ask …",
        )
        return

    await edit_or_send(callback, "Searching…")
    try:
        answer, _ = await answer_question(session, question)
        await edit_or_send(callback, clip_telegram(answer))
    except Exception as exc:  # noqa: BLE001
        await edit_or_send(callback, f"Failed to answer: {exc}")


@router.callback_query(F.data.startswith("act:"))
async def on_action(callback: CallbackQuery, session: AsyncSession) -> None:
    parsed = parse_action_data(callback.data)
    if parsed is None:
        await callback.answer("Invalid callback data", show_alert=True)
        return

    action, pending_id = parsed
    payload = pop_pending(pending_id)
    if payload is None:
        await callback.answer("Buttons expired. Please resend the message.", show_alert=True)
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    await callback.answer()

    if action == "cancel":
        await edit_or_send(callback, "Cancelled.")
        return
    if action == "save":
        await handle_save(callback, session, payload)
        return
    if action == "ask":
        await handle_ask(callback, session, payload)
        return

    await edit_or_send(callback, "Unknown action.")
