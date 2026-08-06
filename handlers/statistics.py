from datetime import date, datetime, time, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import (
    get_appointment_statistics,
    get_income_adjustment_statistics,
)
from keyboards.main import get_main_keyboard
from keyboards.period_calendar import period_calendar_keyboard
from states.statistics import PeriodSelection


router = Router()

MOSCOW_TIMEZONE = timezone(timedelta(hours=3))

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


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


def appointment_word(count: int) -> str:
    last_two_digits = count % 100
    last_digit = count % 10

    if last_two_digits in {11, 12, 13, 14}:
        return "приёмов"

    if last_digit == 1:
        return "приём"

    if last_digit in {2, 3, 4}:
        return "приёма"

    return "приёмов"


def next_month_start(current_date: date) -> date:
    if current_date.month == 12:
        return date(
            year=current_date.year + 1,
            month=1,
            day=1,
        )

    return date(
        year=current_date.year,
        month=current_date.month + 1,
        day=1,
    )


def parse_calendar_callback(
    callback_data: str,
    expected_action: str,
    expected_mode: str,
) -> list[str] | None:
    parts = callback_data.split(":")

    if len(parts) < 5:
        return None

    if parts[0] != "period":
        return None

    if parts[1] != expected_action:
        return None

    if parts[2] != expected_mode:
        return None

    return parts


async def build_statistics_text(
    start_local: datetime,
    end_local: datetime,
    title: str,
    period_label: str,
) -> str:
    start_utc = start_local.astimezone(timezone.utc).isoformat(
        timespec="seconds"
    )
    end_utc = end_local.astimezone(timezone.utc).isoformat(
        timespec="seconds"
    )

    rows = await get_appointment_statistics(
        start_at=start_utc,
        end_at=end_utc,
    )

    (
        adjustment_primary_count,
        adjustment_secondary_count,
        adjustment_amount,
        adjustment_first_date,
        adjustment_last_date,
    ) = await get_income_adjustment_statistics(
        start_date=start_local.date().isoformat(),
        end_date=end_local.date().isoformat(),
    )

    adjustment_count = (
        adjustment_primary_count
        + adjustment_secondary_count
    )

    if not rows and adjustment_count == 0 and adjustment_amount == 0:
        return (
            f"{title}\n"
            f"{period_label}\n\n"
            "Приёмов пока нет."
        )

    clinics: dict[int, dict[str, object]] = {}
    total_count = adjustment_count
    total_amount = adjustment_amount

    for (
        clinic_id,
        clinic_name,
        specialty_id,
        specialty_name,
        visit_type,
        appointment_count,
        row_amount,
    ) in rows:
        row_count = int(appointment_count)
        row_total = int(row_amount)

        total_count += row_count
        total_amount += row_total

        clinic_data = clinics.setdefault(
            int(clinic_id),
            {
                "name": str(clinic_name),
                "specialties": {},
            },
        )

        specialties = clinic_data["specialties"]

        if not isinstance(specialties, dict):
            continue

        specialty_key = (
            int(specialty_id)
            if specialty_id is not None
            else -1
        )

        specialty_data = specialties.setdefault(
            specialty_key,
            {
                "name": str(specialty_name),
                "primary_count": 0,
                "primary_amount": 0,
                "secondary_count": 0,
                "secondary_amount": 0,
            },
        )

        if visit_type == "primary":
            specialty_data["primary_count"] = row_count
            specialty_data["primary_amount"] = row_total
        else:
            specialty_data["secondary_count"] = row_count
            specialty_data["secondary_amount"] = row_total

    lines = [
        title,
        period_label,
        "",
        f"💰 <b>Общая сумма: {format_price(total_amount)} ₽</b>",
        (
            f"Всего приёмов: {total_count} "
            f"{appointment_word(total_count)}"
        ),
        "",
        "📊 <b>Подробная статистика</b>",
        "",
    ]

    for clinic_data in clinics.values():
        clinic_name = escape(str(clinic_data["name"]))
        specialties = clinic_data["specialties"]

        if not isinstance(specialties, dict):
            continue

        lines.append(f"🏥 <b>{clinic_name}</b>")

        for specialty_data in specialties.values():
            specialty_name = escape(
                str(specialty_data["name"])
            )

            primary_count = int(
                specialty_data["primary_count"]
            )
            primary_amount = int(
                specialty_data["primary_amount"]
            )
            secondary_count = int(
                specialty_data["secondary_count"]
            )
            secondary_amount = int(
                specialty_data["secondary_amount"]
            )

            specialty_count = (
                primary_count + secondary_count
            )
            specialty_amount = (
                primary_amount + secondary_amount
            )

            lines.extend(
                [
                    "",
                    f"🩺 <b>{specialty_name}</b>",
                    (
                        f"Первичных: {primary_count} — "
                        f"{format_price(primary_amount)} ₽"
                    ),
                    (
                        f"Повторных: {secondary_count} — "
                        f"{format_price(secondary_amount)} ₽"
                    ),
                    (
                        "Итого по специальности: "
                        f"{specialty_count} "
                        f"{appointment_word(specialty_count)} — "
                        f"{format_price(specialty_amount)} ₽"
                    ),
                ]
            )

        lines.append("")

    if adjustment_count > 0 or adjustment_amount > 0:
        adjustment_period = ""

        if adjustment_first_date and adjustment_last_date:
            first_date = date.fromisoformat(adjustment_first_date)
            last_date = date.fromisoformat(adjustment_last_date)

            if first_date == last_date:
                adjustment_period = first_date.strftime("%d.%m.%Y")
            else:
                adjustment_period = (
                    f"{first_date.strftime('%d.%m.%Y')}–"
                    f"{last_date.strftime('%d.%m.%Y')}"
                )

        lines.extend(
            [
                "📦 <b>Архивные данные без распределения</b>",
                adjustment_period,
                f"Первичных: {adjustment_primary_count}",
                f"Повторных: {adjustment_secondary_count}",
                (
                    "Итого: "
                    f"{adjustment_count} "
                    f"{appointment_word(adjustment_count)} — "
                    f"{format_price(adjustment_amount)} ₽"
                ),
            ]
        )

    return "\n".join(lines).rstrip()


@router.message(F.text == "😺 Сегодня")
async def today_statistics_handler(
    message: Message,
    state: FSMContext,
    is_admin: bool,
) -> None:
    await state.clear()

    current_date = datetime.now(MOSCOW_TIMEZONE).date()

    start_local = datetime.combine(
        current_date,
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )
    end_local = start_local + timedelta(days=1)

    text = await build_statistics_text(
        start_local=start_local,
        end_local=end_local,
        title="😺 <b>Сегодня</b>",
        period_label=current_date.strftime("%d.%m.%Y"),
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin),
    )


@router.message(F.text == "😸 Этот месяц")
async def current_month_statistics_handler(
    message: Message,
    state: FSMContext,
    is_admin: bool,
) -> None:
    await state.clear()

    current_date = datetime.now(MOSCOW_TIMEZONE).date()
    month_start = date(
        year=current_date.year,
        month=current_date.month,
        day=1,
    )
    following_month_start = next_month_start(month_start)

    start_local = datetime.combine(
        month_start,
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )
    end_local = datetime.combine(
        following_month_start,
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )

    text = await build_statistics_text(
        start_local=start_local,
        end_local=end_local,
        title="😸 <b>Этот месяц</b>",
        period_label=(
            f"{MONTH_NAMES[current_date.month]} "
            f"{current_date.year}"
        ),
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin),
    )

@router.message(F.text == "🐈‍⬛ Выбрать период")
async def start_period_selection_handler(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(PeriodSelection.choosing_start)

    today = datetime.now(MOSCOW_TIMEZONE).date()

    await message.answer(
        "🗓 <b>Выберите начальную дату</b>",
        reply_markup=period_calendar_keyboard(
            mode="start",
            year=today.year,
            month=today.month,
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "period:noop")
async def period_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "period:cancel")
async def cancel_period_selection_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Выбор периода отменён."
        )

    await callback.answer()


@router.callback_query(
    PeriodSelection.choosing_start,
    F.data.startswith("period:nav:start:"),
)
async def navigate_start_calendar_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = parse_calendar_callback(
        callback.data,
        expected_action="nav",
        expected_mode="start",
    )

    if parts is None or len(parts) != 5:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    year_text = parts[3]
    month_text = parts[4]

    if not year_text.isdigit() or not month_text.isdigit():
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    year = int(year_text)
    month = int(month_text)

    if year < 2000 or year > 2100 or month < 1 or month > 12:
        await callback.answer(
            "Дата вне допустимого диапазона.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=period_calendar_keyboard(
                mode="start",
                year=year,
                month=month,
            )
        )

    await callback.answer()


@router.callback_query(
    PeriodSelection.choosing_start,
    F.data.startswith("period:day:start:"),
)
async def select_start_date_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = parse_calendar_callback(
        callback.data,
        expected_action="day",
        expected_mode="start",
    )

    if parts is None or len(parts) != 6:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    date_parts = parts[3:6]

    if not all(part.isdigit() for part in date_parts):
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    try:
        selected_start = date(
            int(date_parts[0]),
            int(date_parts[1]),
            int(date_parts[2]),
        )
    except ValueError:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    await state.update_data(
        start_date=selected_start.isoformat()
    )
    await state.set_state(PeriodSelection.choosing_end)

    if callback.message:
        await callback.message.edit_text(
            "🗓 <b>Выберите конечную дату</b>\n\n"
            f"Начало: {selected_start.strftime('%d.%m.%Y')}",
            reply_markup=period_calendar_keyboard(
                mode="end",
                year=selected_start.year,
                month=selected_start.month,
                selected_start=selected_start,
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(
    PeriodSelection.choosing_end,
    F.data.startswith("period:nav:end:"),
)
async def navigate_end_calendar_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = parse_calendar_callback(
        callback.data,
        expected_action="nav",
        expected_mode="end",
    )

    if parts is None or len(parts) != 5:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    year_text = parts[3]
    month_text = parts[4]

    if not year_text.isdigit() or not month_text.isdigit():
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    year = int(year_text)
    month = int(month_text)

    if year < 2000 or year > 2100 or month < 1 or month > 12:
        await callback.answer(
            "Дата вне допустимого диапазона.",
            show_alert=True,
        )
        return

    data = await state.get_data()
    start_date_text = data.get("start_date")

    if not start_date_text:
        await state.clear()
        await callback.answer(
            "Начальная дата потеряна. Выберите период заново.",
            show_alert=True,
        )
        return

    selected_start = date.fromisoformat(str(start_date_text))

    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=period_calendar_keyboard(
                mode="end",
                year=year,
                month=month,
                selected_start=selected_start,
            )
        )

    await callback.answer()


@router.callback_query(
    PeriodSelection.choosing_end,
    F.data.startswith("period:day:end:"),
)
async def select_end_date_handler(
    callback: CallbackQuery,
    state: FSMContext,
    is_admin: bool,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = parse_calendar_callback(
        callback.data,
        expected_action="day",
        expected_mode="end",
    )

    if parts is None or len(parts) != 6:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    date_parts = parts[3:6]

    if not all(part.isdigit() for part in date_parts):
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    try:
        selected_end = date(
            int(date_parts[0]),
            int(date_parts[1]),
            int(date_parts[2]),
        )
    except ValueError:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    data = await state.get_data()
    start_date_text = data.get("start_date")

    if not start_date_text:
        await state.clear()
        await callback.answer(
            "Начальная дата потеряна. Выберите период заново.",
            show_alert=True,
        )
        return

    selected_start = date.fromisoformat(str(start_date_text))

    if selected_end < selected_start:
        await callback.answer(
            "Конечная дата не может быть раньше начальной.",
            show_alert=True,
        )
        return

    start_local = datetime.combine(
        selected_start,
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )
    end_local = datetime.combine(
        selected_end + timedelta(days=1),
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )

    text = await build_statistics_text(
        start_local=start_local,
        end_local=end_local,
        title="🗓 <b>Выбранный период</b>",
        period_label=(
            f"{selected_start.strftime('%d.%m.%Y')} — "
            f"{selected_end.strftime('%d.%m.%Y')}"
        ),
    )

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard(is_admin),
        )

    await callback.answer("Статистика рассчитана")
