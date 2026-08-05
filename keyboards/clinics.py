from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def clinics_menu_keyboard(
    clinics: list[tuple[int, str, int, int]],
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="🐱 Добавить поликлинику",
                callback_data="clinic:add",
            ),
        ],
    ]

    for clinic_id, name, _, _ in clinics:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"😼 Изменить цены: {name}",
                    callback_data=f"clinic:edit:{clinic_id}",
                ),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="❌ Отмена"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


edit_prices_confirmation_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Сохранить новые цены",
                callback_data="clinic:edit:save",
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить изменение",
                callback_data="clinic:edit:cancel",
            ),
        ],
    ]
)
