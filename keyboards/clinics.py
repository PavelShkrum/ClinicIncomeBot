from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


KEEP_NAME_TEXT = "➡️ Оставить текущее название"
KEEP_PRICE_TEXT = "➡️ Оставить текущую цену"


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
                    text=f"✏️ Изменить: {name}",
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


edit_name_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=KEEP_NAME_TEXT),
        ],
        [
            KeyboardButton(text="❌ Отмена"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


edit_price_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=KEEP_PRICE_TEXT),
        ],
        [
            KeyboardButton(text="❌ Отмена"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


edit_clinic_confirmation_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Сохранить изменения",
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