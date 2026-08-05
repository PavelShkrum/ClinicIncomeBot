from datetime import date, datetime, time, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database.db import (
    add_appointment,
    get_clinic_by_id,
    get_clinics,
)
from keyboards.appointment_date import (
    appointment_date_calendar_keyboard,
)
from keyboards.appointments import (
    appointment_clinics_keyboard,
    appointment_type_keyboard,
    backdated_clinics_keyboard,
    backdated_confirmation_keyboard,
    backdated_result_keyboard,
    backdated_type_keyboard,
)
from keyboards.main import get_main_keyboard


router = Router()

MOSCOW_TIMEZONE = timezone(timedelta(hours=3))


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


def parse_iso_date(date_text: str) -> date | None:
    try:
        parsed_date = date.fromisoformat(date_text)
    except ValueError:
        return None

    if parsed_date > datetime.now(MOSCOW_TIMEZONE).date():
        return None

    return parsed_date


async def show_clinic_selection(
    message: Message,
    is_admin: bool,
    edit_message: bool = False,
) -> None:
    clinics = await get_clinics()

    if not clinics:
        text = (
            "Поликлиники пока не настроены.\n\n"
            "Обратитесь к администратору бота."
        )

        if edit_message:
            await message.edit_text(text)
        else:
            await message.answer(
                text,
                reply_markup=get_main_keyboard(is_admin),
            )

        return

    text = "Выберите поликлинику:"

    if edit_message:
        await message.edit_text(
            text,
            reply_markup=appointment_clinics_keyboard(clinics),
        )
    else:
        await message.answer(
            text,
            reply_markup=appointment_clinics_keyboard(clinics),
        )


async def show_backdated_clinic_selection(
    message: Message,
    selected_date: date,
    edit_message: bool,
) -> None:
    clinics = await get_clinics()

    if not clinics:
        text = (
            "Поликлиники пока не настроены.\n\n"
            "Сначала добавьте поликлинику и цены."
        )

        if edit_message:
            await message.edit_text(text)
        else:
            await message.answer(text)

        return

    text = (
        "📅 <b>Добавление приёма за дату</b>\n\n"
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
        "Выберите поликлинику:"
    )
    keyboard = backdated_clinics_keyboard(
        clinics=clinics,
        appointment_date=selected_date,
    )

    if edit_message:
        await message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.message(F.text == "🐾 Добавить приём")
async def start_add_appointment_handler(
    message: Message,
    is_admin: bool,
) -> None:
    await show_clinic_selection(
        message=message,
        is_admin=is_admin,
    )


@router.message(F.text == "📅 Добавить за дату")
async def start_backdated_appointment_handler(
    message: Message,
) -> None:
    today = datetime.now(MOSCOW_TIMEZONE).date()

    await message.answer(
        "📅 <b>Выберите дату приёма</b>\n\n"
        "Можно выбрать сегодняшний день или прошедшую дату.",
        reply_markup=appointment_date_calendar_keyboard(
            year=today.year,
            month=today.month,
            today=today,
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "appointment:back")
async def appointment_back_handler(
    callback: CallbackQuery,
    is_admin: bool,
) -> None:
    if callback.message:
        await show_clinic_selection(
            message=callback.message,
            is_admin=is_admin,
            edit_message=True,
        )

    await callback.answer()


@router.callback_query(F.data == "appointment:cancel")
async def cancel_appointment_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Добавление приёма отменено."
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("appointment:clinic:")
)
async def select_clinic_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    clinic_id_text = callback.data.rsplit(":", maxsplit=1)[-1]

    if not clinic_id_text.isdigit():
        await callback.answer(
            "Некорректная поликлиника.",
            show_alert=True,
        )
        return

    clinic_id = int(clinic_id_text)
    clinic = await get_clinic_by_id(clinic_id)

    if clinic is None:
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    _, name, primary_price, secondary_price = clinic

    if callback.message:
        await callback.message.edit_text(
            f"🏥 <b>{escape(name)}</b>\n\n"
            "Выберите тип приёма:",
            reply_markup=appointment_type_keyboard(
                clinic_id=clinic_id,
                primary_price=primary_price,
                secondary_price=secondary_price,
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("appointment:type:")
)
async def select_appointment_type_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    callback_parts = callback.data.split(":")

    if len(callback_parts) != 4:
        await callback.answer(
            "Некорректные данные.",
            show_alert=True,
        )
        return

    clinic_id_text = callback_parts[2]
    visit_type = callback_parts[3]

    if not clinic_id_text.isdigit():
        await callback.answer(
            "Некорректная поликлиника.",
            show_alert=True,
        )
        return

    if visit_type not in {"primary", "secondary"}:
        await callback.answer(
            "Некорректный тип приёма.",
            show_alert=True,
        )
        return

    clinic_id = int(clinic_id_text)

    result = await add_appointment(
        clinic_id=clinic_id,
        visit_type=visit_type,
    )

    if result is None:
        await callback.answer(
            "Не удалось добавить приём.",
            show_alert=True,
        )
        return

    clinic_name, amount = result

    visit_type_name = (
        "Первичный"
        if visit_type == "primary"
        else "Вторичный"
    )

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Приём добавлен</b>\n\n"
            f"🏥 {escape(clinic_name)}\n"
            f"Тип: {visit_type_name}\n"
            f"Сумма: {format_price(amount)} ₽",
            parse_mode="HTML",
        )

    await callback.answer("Приём сохранён")


@router.callback_query(F.data == "past:noop")
async def backdated_noop_handler(
    callback: CallbackQuery,
) -> None:
    await callback.answer()


@router.callback_query(F.data == "past:cancel")
async def cancel_backdated_appointment_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Добавление приёма за дату отменено."
        )

    await callback.answer()


@router.callback_query(F.data == "past:done")
async def finish_backdated_appointment_handler(
    callback: CallbackQuery,
    is_admin: bool,
) -> None:
    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
        await callback.message.answer(
            "Готово. Выберите следующее действие:",
            reply_markup=get_main_keyboard(is_admin),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("past:nav:"))
async def navigate_backdated_calendar_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "Некорректный месяц.",
            show_alert=True,
        )
        return

    year_text = parts[2]
    month_text = parts[3]

    if not year_text.isdigit() or not month_text.isdigit():
        await callback.answer(
            "Некорректный месяц.",
            show_alert=True,
        )
        return

    year = int(year_text)
    month = int(month_text)
    today = datetime.now(MOSCOW_TIMEZONE).date()

    if year < 2000 or month < 1 or month > 12:
        await callback.answer(
            "Дата вне допустимого диапазона.",
            show_alert=True,
        )
        return

    if date(year, month, 1) > date(
        today.year,
        today.month,
        1,
    ):
        await callback.answer(
            "Будущую дату выбрать нельзя.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=appointment_date_calendar_keyboard(
                year=year,
                month=month,
                today=today,
            )
        )

    await callback.answer()


@router.callback_query(F.data.startswith("past:calendar:"))
async def return_to_backdated_calendar_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "Некорректный месяц.",
            show_alert=True,
        )
        return

    year_text = parts[2]
    month_text = parts[3]

    if not year_text.isdigit() or not month_text.isdigit():
        await callback.answer(
            "Некорректный месяц.",
            show_alert=True,
        )
        return

    year = int(year_text)
    month = int(month_text)
    today = datetime.now(MOSCOW_TIMEZONE).date()

    if year < 2000 or month < 1 or month > 12:
        await callback.answer(
            "Дата вне допустимого диапазона.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "📅 <b>Выберите дату приёма</b>\n\n"
            "Можно выбрать сегодняшний день или прошедшую дату.",
            reply_markup=appointment_date_calendar_keyboard(
                year=year,
                month=month,
                today=today,
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data.startswith("past:day:"))
async def select_backdated_day_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")

    if len(parts) != 5:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    date_parts = parts[2:5]

    if not all(part.isdigit() for part in date_parts):
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    try:
        selected_date = date(
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

    if selected_date > datetime.now(MOSCOW_TIMEZONE).date():
        await callback.answer(
            "Будущую дату выбрать нельзя.",
            show_alert=True,
        )
        return

    if callback.message:
        await show_backdated_clinic_selection(
            message=callback.message,
            selected_date=selected_date,
            edit_message=True,
        )

    await callback.answer()


@router.callback_query(F.data.startswith("past:clinics:"))
async def reopen_backdated_clinics_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    date_text = callback.data.split(":", maxsplit=2)[-1]
    selected_date = parse_iso_date(date_text)

    if selected_date is None:
        await callback.answer(
            "Некорректная дата.",
            show_alert=True,
        )
        return

    if callback.message:
        await show_backdated_clinic_selection(
            message=callback.message,
            selected_date=selected_date,
            edit_message=True,
        )

    await callback.answer()


@router.callback_query(F.data.startswith("past:clinic:"))
async def select_backdated_clinic_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "Некорректные данные.",
            show_alert=True,
        )
        return

    selected_date = parse_iso_date(parts[2])
    clinic_id_text = parts[3]

    if selected_date is None or not clinic_id_text.isdigit():
        await callback.answer(
            "Некорректные данные.",
            show_alert=True,
        )
        return

    clinic_id = int(clinic_id_text)
    clinic = await get_clinic_by_id(clinic_id)

    if clinic is None:
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    _, name, primary_price, secondary_price = clinic

    if callback.message:
        await callback.message.edit_text(
            "📅 <b>Добавление приёма за дату</b>\n\n"
            f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
            f"Поликлиника: <b>{escape(name)}</b>\n\n"
            "Выберите тип приёма:",
            reply_markup=backdated_type_keyboard(
                appointment_date=selected_date,
                clinic_id=clinic_id,
                primary_price=primary_price,
                secondary_price=secondary_price,
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data.startswith("past:type:"))
async def select_backdated_type_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")

    if len(parts) != 5:
        await callback.answer(
            "Некорректные данные.",
            show_alert=True,
        )
        return

    selected_date = parse_iso_date(parts[2])
    clinic_id_text = parts[3]
    visit_type = parts[4]

    if (
        selected_date is None
        or not clinic_id_text.isdigit()
        or visit_type not in {"primary", "secondary"}
    ):
        await callback.answer(
            "Некорректные данные.",
            show_alert=True,
        )
        return

    clinic_id = int(clinic_id_text)
    clinic = await get_clinic_by_id(clinic_id)

    if clinic is None:
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    _, name, primary_price, secondary_price = clinic
    amount = (
        primary_price
        if visit_type == "primary"
        else secondary_price
    )
    visit_type_name = (
        "Первичный"
        if visit_type == "primary"
        else "Вторичный"
    )

    if callback.message:
        await callback.message.edit_text(
            "Проверьте данные:\n\n"
            f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
            f"🏥 Поликлиника: <b>{escape(name)}</b>\n"
            f"Тип: <b>{visit_type_name}</b>\n"
            f"Сумма: <b>{format_price(amount)} ₽</b>\n\n"
            "Сохранить приём?",
            reply_markup=backdated_confirmation_keyboard(
                appointment_date=selected_date,
                clinic_id=clinic_id,
                visit_type=visit_type,
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data.startswith("past:confirm:"))
async def confirm_backdated_appointment_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")

    if len(parts) != 5:
        await callback.answer(
            "Некорректные данные.",
            show_alert=True,
        )
        return

    selected_date = parse_iso_date(parts[2])
    clinic_id_text = parts[3]
    visit_type = parts[4]

    if (
        selected_date is None
        or not clinic_id_text.isdigit()
        or visit_type not in {"primary", "secondary"}
    ):
        await callback.answer(
            "Некорректные данные.",
            show_alert=True,
        )
        return

    clinic_id = int(clinic_id_text)
    local_datetime = datetime.combine(
        selected_date,
        time(hour=12),
        tzinfo=MOSCOW_TIMEZONE,
    )
    created_at = local_datetime.astimezone(
        timezone.utc
    ).isoformat(timespec="seconds")

    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    result = await add_appointment(
        clinic_id=clinic_id,
        visit_type=visit_type,
        created_at=created_at,
    )

    if result is None:
        await callback.answer(
            "Не удалось добавить приём.",
            show_alert=True,
        )
        return

    clinic_name, amount = result
    visit_type_name = (
        "Первичный"
        if visit_type == "primary"
        else "Вторичный"
    )

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Приём за дату добавлен</b>\n\n"
            f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n"
            f"🏥 {escape(clinic_name)}\n"
            f"Тип: {visit_type_name}\n"
            f"Сумма: {format_price(amount)} ₽",
            reply_markup=backdated_result_keyboard(
                appointment_date=selected_date,
            ),
            parse_mode="HTML",
        )

    await callback.answer("Приём сохранён")