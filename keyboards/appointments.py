from datetime import date

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


def appointment_specialties_keyboard(
    clinic_id: int,
    specialties: list[tuple[int, str, int, int]],
) -> InlineKeyboardMarkup:
    buttons = []

    for specialty_id, name, _, _ in specialties:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🩺 {name}",
                    callback_data=(
                        f"appointment:specialty:"
                        f"{clinic_id}:{specialty_id}"
                    ),
                )
            ]
        )

    buttons.extend(
        [
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

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def appointment_type_keyboard(
    clinic_id: int,
    specialty_id: int,
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
                        f"appointment:type:{clinic_id}:"
                        f"{specialty_id}:primary"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "Повторный — "
                        f"{format_price(secondary_price)} ₽"
                    ),
                    callback_data=(
                        f"appointment:type:{clinic_id}:"
                        f"{specialty_id}:secondary"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Выбрать другую специальность",
                    callback_data=f"appointment:clinic:{clinic_id}",
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


def backdated_clinics_keyboard(
    clinics: list[tuple[int, str, int, int]],
    appointment_date: date,
) -> InlineKeyboardMarkup:
    date_text = appointment_date.isoformat()
    buttons = []

    for clinic_id, name, _, _ in clinics:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🏥 {name}",
                    callback_data=(
                        f"past:clinic:{date_text}:{clinic_id}"
                    ),
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="⬅️ Выбрать другую дату",
                    callback_data=(
                        f"past:calendar:{appointment_date.year}:"
                        f"{appointment_date.month}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="past:cancel",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def backdated_specialties_keyboard(
    appointment_date: date,
    clinic_id: int,
    specialties: list[tuple[int, str, int, int]],
) -> InlineKeyboardMarkup:
    date_text = appointment_date.isoformat()
    buttons = []

    for specialty_id, name, _, _ in specialties:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🩺 {name}",
                    callback_data=(
                        f"past:specialty:{date_text}:"
                        f"{clinic_id}:{specialty_id}"
                    ),
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="⬅️ Другая поликлиника",
                    callback_data=f"past:clinics:{date_text}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="past:cancel",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def backdated_type_keyboard(
    appointment_date: date,
    clinic_id: int,
    specialty_id: int,
    primary_price: int,
    secondary_price: int,
) -> InlineKeyboardMarkup:
    date_text = appointment_date.isoformat()

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        "Первичный — "
                        f"{format_price(primary_price)} ₽"
                    ),
                    callback_data=(
                        f"past:type:{date_text}:{clinic_id}:"
                        f"{specialty_id}:primary"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "Повторный — "
                        f"{format_price(secondary_price)} ₽"
                    ),
                    callback_data=(
                        f"past:type:{date_text}:{clinic_id}:"
                        f"{specialty_id}:secondary"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Другая специальность",
                    callback_data=(
                        f"past:clinic:{date_text}:{clinic_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="past:cancel",
                )
            ],
        ]
    )


def backdated_confirmation_keyboard(
    appointment_date: date,
    clinic_id: int,
    specialty_id: int,
    visit_type: str,
) -> InlineKeyboardMarkup:
    date_text = appointment_date.isoformat()

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Сохранить приём",
                    callback_data=(
                        f"past:confirm:{date_text}:{clinic_id}:"
                        f"{specialty_id}:{visit_type}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Изменить тип",
                    callback_data=(
                        f"past:specialty:{date_text}:"
                        f"{clinic_id}:{specialty_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="past:cancel",
                )
            ],
        ]
    )


def backdated_result_keyboard(
    appointment_date: date,
) -> InlineKeyboardMarkup:
    date_text = appointment_date.isoformat()

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Ещё приём на эту дату",
                    callback_data=f"past:clinics:{date_text}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Готово",
                    callback_data="past:done",
                )
            ],
        ]
    )
