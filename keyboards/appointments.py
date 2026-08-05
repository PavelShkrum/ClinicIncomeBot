from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


def appointment_clinics_keyboard(
    clinics: list[tuple[int, str, int, int]],
) -> InlineKeyboardMarkup:
    buttons = []

    for clinic_id, name, _, _ in clinics:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🏥 {name}",
                    callback_data=f"appointment:clinic:{clinic_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="appointment:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def appointment_type_keyboard(
    clinic_id: int,
    primary_price: int,
    secondary_price: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        "Первичный — "
                        f"{format_price(primary_price)} ₽"
                    ),
                    callback_data=(
                        f"appointment:type:{clinic_id}:primary"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "Вторичный — "
                        f"{format_price(secondary_price)} ₽"
                    ),
                    callback_data=(
                        f"appointment:type:{clinic_id}:secondary"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Выбрать другую поликлинику",
                    callback_data="appointment:back",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="appointment:cancel",
                )
            ],
        ]
    )
