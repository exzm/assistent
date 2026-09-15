from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def pending_action_keyboard(pending_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сохранить", callback_data=f"act:save:{pending_id}"),
                InlineKeyboardButton(text="Это вопрос", callback_data=f"act:ask:{pending_id}"),
            ],
            [InlineKeyboardButton(text="Отмена", callback_data=f"act:cancel:{pending_id}")],
        ]
    )
