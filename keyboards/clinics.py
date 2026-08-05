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
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text=f"✏️ Изменить всё: {name}",
                        callback_data=f"clinic:edit:{clinic_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"💰 Изменить цены: {name}",
                        callback_data=f"clinic:prices:{clinic_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"🗑 Удалить: {name}",
                        callback_data=f"clinic:delete:{clinic_id}",
                    ),
                ],
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


def delete_clinic_confirmation_keyboard(
    clinic_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=(
                        f"clinic:delete:confirm:{clinic_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Нет, отменить",
                    callback_data="clinic:delete:cancel",
                ),
            ],
        ]
    )
