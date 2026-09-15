from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def pending_action_keyboard(pending_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Save", callback_data=f"act:save:{pending_id}"),
                InlineKeyboardButton(text="This is a question", callback_data=f"act:ask:{pending_id}"),
            ],
            [InlineKeyboardButton(text="Cancel", callback_data=f"act:cancel:{pending_id}")],
        ]
    )
