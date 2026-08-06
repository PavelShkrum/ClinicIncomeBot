from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def specialties_menu_keyboard(
    clinic_id: int,
    specialties: list[tuple[int, str, int, int]],
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="➕ Добавить специальность",
                callback_data=f"specialty:add:{clinic_id}",
            )
        ]
    ]

    for specialty_id, name, _, _ in specialties:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"⚙️ {name}",
                    callback_data=f"specialty:manage:{specialty_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к поликлиникам",
                callback_data="specialty:back",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def specialty_management_keyboard(
    specialty_id: int,
    clinic_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить название и цены",
                    callback_data=f"specialty:edit:{specialty_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить специальность",
                    callback_data=f"specialty:delete:{specialty_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к специальностям",
                    callback_data=f"specialty:list:{clinic_id}",
                )
            ],
        ]
    )


def specialty_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Сохранить",
                    callback_data=f"specialty:{action}:save",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"specialty:{action}:cancel",
                )
            ],
        ]
    )


def delete_specialty_confirmation_keyboard(
    specialty_id: int,
    clinic_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=(
                        f"specialty:delete:confirm:{specialty_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Нет, отменить",
                    callback_data=f"specialty:list:{clinic_id}",
                )
            ],
        ]
    )
