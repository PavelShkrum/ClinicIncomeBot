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
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text=f"🩺 Специальности: {name}",
                        callback_data=f"specialty:list:{clinic_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"✏️ Изменить название: {name}",
                        callback_data=f"clinic:rename:{clinic_id}",
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


add_clinic_confirmation_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Сохранить поликлинику",
                callback_data="clinic:add:save",
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="clinic:add:cancel",
            ),
        ],
    ]
)


rename_clinic_confirmation_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Сохранить название",
                callback_data="clinic:rename:save",
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="clinic:rename:cancel",
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
