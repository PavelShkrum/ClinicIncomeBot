import calendar
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

WEEKDAY_NAMES = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def shift_month(
    year: int,
    month: int,
    offset: int,
) -> tuple[int, int]:
    month_index = year * 12 + (month - 1) + offset
    new_year, new_month_index = divmod(month_index, 12)

    return new_year, new_month_index + 1


def appointment_date_calendar_keyboard(
    year: int,
    month: int,
    today: date,
) -> InlineKeyboardMarkup:
    previous_year, previous_month = shift_month(year, month, -1)
    next_year, next_month = shift_month(year, month, 1)

    current_month_start = date(today.year, today.month, 1)
    next_month_start = date(next_year, next_month, 1)

    next_callback = (
        f"past:nav:{next_year}:{next_month}"
        if next_month_start <= current_month_start
        else "past:noop"
    )

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="◀️",
                callback_data=(
                    f"past:nav:{previous_year}:{previous_month}"
                ),
            ),
            InlineKeyboardButton(
                text=f"{MONTH_NAMES[month]} {year}",
                callback_data="past:noop",
            ),
            InlineKeyboardButton(
                text="▶️" if next_callback != "past:noop" else "·",
                callback_data=next_callback,
            ),
        ],
        [
            InlineKeyboardButton(
                text=weekday,
                callback_data="past:noop",
            )
            for weekday in WEEKDAY_NAMES
        ],
    ]

    for week in calendar.monthcalendar(year, month):
        week_buttons: list[InlineKeyboardButton] = []

        for day_number in week:
            if day_number == 0:
                week_buttons.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data="past:noop",
                    )
                )
                continue

            selected_date = date(year, month, day_number)

            if selected_date > today:
                week_buttons.append(
                    InlineKeyboardButton(
                        text="·",
                        callback_data="past:noop",
                    )
                )
                continue

            button_text = str(day_number)

            if selected_date == today:
                button_text = f"● {day_number}"

            week_buttons.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=(
                        f"past:day:{year}:{month}:{day_number}"
                    ),
                )
            )

        rows.append(week_buttons)

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="past:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)