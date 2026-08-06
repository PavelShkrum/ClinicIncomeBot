from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def delete_record_keyboard(
    record_type: str,
    record_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="😿 Удалить запись",
                    callback_data=(
                        f"history:delete:{record_type}:{record_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="😺 Оставить запись",
                    callback_data="history:keep",
                )
            ],
        ]
    )
