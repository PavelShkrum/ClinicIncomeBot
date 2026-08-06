from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def daily_clinics_keyboard(
    clinics: list[tuple[int, str, int, int]],
    selected_date: date,
) -> InlineKeyboardMarkup:
    date_text = selected_date.isoformat()
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🏥 {name}",
                callback_data=f"daily:clinic:{date_text}:{clinic_id}",
            )
        ]
        for clinic_id, name, _, _ in clinics
    ]
    buttons.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="daily:cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def daily_specialties_keyboard(
    selected_date: date,
    clinic_id: int,
    specialties: list[tuple[int, str, int, int]],
) -> InlineKeyboardMarkup:
    date_text = selected_date.isoformat()
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🩺 {name}",
                callback_data=(
                    f"daily:specialty:{date_text}:{clinic_id}:{specialty_id}"
                ),
            )
        ]
        for specialty_id, name, _, _ in specialties
    ]
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="⬅️ Другая поликлиника",
                    callback_data=f"daily:clinics:{date_text}",
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="daily:cancel")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


count_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="0")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


daily_confirmation_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Сохранить дневной итог",
                callback_data="daily:save",
            )
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="daily:cancel")],
    ]
)


def daily_result_keyboard(selected_date: date) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Ещё запись за этот день",
                    callback_data=f"daily:clinics:{selected_date.isoformat()}",
                )
            ],
            [InlineKeyboardButton(text="✅ Готово", callback_data="daily:done")],
        ]
    )
