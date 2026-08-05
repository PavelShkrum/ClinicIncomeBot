from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def delete_appointment_keyboard(
    appointment_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="😿 Удалить запись",
                    callback_data=(
                        f"history:delete:{appointment_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="😺 Оставить запись",
                    callback_data="history:keep",
                ),
            ],
        ]
    )
