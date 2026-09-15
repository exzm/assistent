from io import BytesIO

from aiogram.types import Message


async def download_telegram_file(message: Message, file_id: str) -> bytes:
    buf = BytesIO()
    await message.bot.download(file=file_id, destination=buf)
    return buf.getvalue()
