from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.services.cards import format_item_card, format_cards
from app.services.textutil import clip_telegram

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Личный memory-бот.\n\n"
        "Пришли фото, PDF, голос, заметку или пересланное сообщение — "
        "появятся кнопки «Сохранить» / «Это вопрос».\n\n"
        "Команды:\n"
        "/recent — последние записи\n"
        "/get <id> — оригинал файла\n"
        "/ask <вопрос> — сразу спросить без кнопок"
    )


@router.message(Command("recent"))
async def cmd_recent(message: Message, session: AsyncSession) -> None:
    items = await repository.list_recent(session, limit=10)
    if not items:
        await message.answer("Пока пусто.")
        return
    await message.answer(clip_telegram(format_cards(list(items), limit=10)))


@router.message(Command("get"))
async def cmd_get(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Использование: /get <id>")
        return
    item_id = int(command.args.strip())
    item = await repository.get_item(session, item_id)
    if not item:
        await message.answer(f"Запись #{item_id} не найдена.")
        return
    await message.answer(format_item_card(item))
    if item.file_path:
        try:
            await message.answer_document(FSInputFile(item.file_path))
        except Exception:
            await message.answer(f"Файл на диске недоступен: {item.file_path}")
    else:
        await message.answer("У этой записи нет сохранённого файла.")


@router.message(Command("ask"))
async def cmd_ask(message: Message, command: CommandObject, session: AsyncSession) -> None:
    from app.services.rag import answer_question

    question = (command.args or "").strip()
    if not question:
        await message.answer("Использование: /ask когда я менял масло?")
        return
    status = await message.answer("Ищу…")
    try:
        answer, _ = await answer_question(session, question)
        await status.edit_text(clip_telegram(answer))
    except Exception as exc:
        await status.edit_text(f"Ошибка поиска: {exc}")
