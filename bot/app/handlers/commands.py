from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.services.cards import format_cards, format_item_card
from app.services.rag import answer_question
from app.utils.text import clip_telegram, escape_html

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Personal memory bot.\n\n"
        "Send a photo, PDF, voice note, text, or forwarded message — "
        "then choose Save / This is a question.\n\n"
        "Commands:\n"
        "/recent — latest records\n"
        "/get <id> — original file\n"
        "/ask <question> — ask without buttons"
    )


@router.message(Command("recent"))
async def cmd_recent(message: Message, session: AsyncSession) -> None:
    items = await repository.list_recent(session, limit=10)
    if not items:
        await message.answer("Nothing saved yet.")
        return
    await message.answer(clip_telegram(format_cards(list(items), limit=10)))


@router.message(Command("get"))
async def cmd_get(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /get <id>")
        return
    item_id = int(command.args.strip())
    item = await repository.get_item(session, item_id)
    if not item:
        await message.answer(f"Record #{item_id} not found.")
        return
    await message.answer(clip_telegram(format_item_card(item)))
    if item.file_path:
        try:
            await message.answer_document(FSInputFile(item.file_path))
        except Exception:  # noqa: BLE001
            await message.answer(f"File is unavailable on disk: {item.file_path}")
    else:
        await message.answer("This record has no stored file.")


@router.message(Command("ask"))
async def cmd_ask(message: Message, command: CommandObject, session: AsyncSession) -> None:
    question = (command.args or "").strip()
    if not question:
        await message.answer("Usage: /ask when did I change the oil?")
        return
    status = await message.answer("Searching…")
    try:
        answer, _ = await answer_question(session, question)
        await status.edit_text(clip_telegram(answer))
    except Exception as exc:  # noqa: BLE001
        await status.edit_text(f"Search failed: {escape_html(str(exc))}")
