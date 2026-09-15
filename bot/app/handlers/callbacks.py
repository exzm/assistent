from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cards import format_item_card
from app.services.ingest import ingest_payload
from app.services.pending import pop_pending
from app.services.query_text import materialize_query_text
from app.services.rag import answer_question
from app.services.textutil import clip_telegram

router = Router(name="callbacks")


@router.callback_query(F.data.startswith("act:"))
async def on_action(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    _, action, pending_id = parts
    payload = pop_pending(pending_id)
    if not payload:
        await callback.answer("Срок действия кнопок истёк. Пришли сообщение снова.", show_alert=True)
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    await callback.answer()

    if action == "cancel":
        if callback.message:
            await callback.message.edit_text("Отменено.")
        return

    if action == "save":
        if callback.message:
            await callback.message.edit_text("Сохраняю…")
        try:
            item = await ingest_payload(session, payload)
            text = clip_telegram("Сохранено.\n\n" + format_item_card(item))
            if callback.message:
                await callback.message.edit_text(text)
            else:
                await callback.bot.send_message(callback.from_user.id, text)
        except Exception as exc:
            err = f"Не удалось сохранить: {exc}"
            if callback.message:
                await callback.message.edit_text(err)
            else:
                await callback.bot.send_message(callback.from_user.id, err)
        return

    if action == "ask":
        if callback.message:
            await callback.message.edit_text("Готовлю вопрос…")
        try:
            question = await materialize_query_text(payload)
        except Exception as exc:
            if callback.message:
                await callback.message.edit_text(f"Не удалось подготовить вопрос: {exc}")
            return

        if not question:
            if callback.message:
                await callback.message.edit_text(
                    "Не удалось получить текст вопроса. Напиши вопрос текстом или /ask …"
                )
            return

        if callback.message:
            await callback.message.edit_text("Ищу ответ…")
        try:
            answer, _ = await answer_question(session, question)
            answer = clip_telegram(answer)
            if callback.message:
                await callback.message.edit_text(answer)
            else:
                await callback.bot.send_message(callback.from_user.id, answer)
        except Exception as exc:
            err = f"Не удалось ответить: {exc}"
            if callback.message:
                await callback.message.edit_text(err)
            else:
                await callback.bot.send_message(callback.from_user.id, err)
        return

    if callback.message:
        await callback.message.edit_text("Неизвестное действие.")
