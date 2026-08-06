from datetime import date, datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import (
    get_clinic_by_id,
    get_clinics,
    get_daily_entry_by_key,
    get_specialties,
    get_specialty_by_id,
    save_daily_entry,
)
from keyboards.appointment_date import appointment_date_calendar_keyboard
from keyboards.appointments import (
    count_keyboard,
    daily_clinics_keyboard,
    daily_confirmation_keyboard,
    daily_result_keyboard,
    daily_specialties_keyboard,
)
from keyboards.main import get_main_keyboard
from states.daily_entry import DailyEntry


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


def parse_count(text: str) -> int | None:
    normalized = text.strip().replace(" ", "")

    if not normalized.isdigit():
        return None

    count = int(normalized)
    return count if 0 <= count <= 1000 else None


async def show_daily_clinics(
    message: Message,
    selected_date: date,
    edit_message: bool = False,
) -> None:
    clinics = await get_clinics()

    if not clinics:
        text = (
            "Поликлиники пока не настроены.\n\n"
            "Сначала добавьте поликлинику и специальность."
        )
        if edit_message:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    text = (
        "📋 <b>Дневной итог</b>\n\n"
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
        "🏥 Выберите поликлинику:"
    )
    keyboard = daily_clinics_keyboard(clinics, selected_date)

    if edit_message:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text.in_({"🐾 Добавить за сегодня", "🐾 Добавить приём"}))
async def start_today_entry_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_daily_clinics(
        message=message,
        selected_date=datetime.now(MOSCOW_TIMEZONE).date(),
    )


@router.message(F.text == "📅 Добавить за дату")
async def start_dated_entry_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    today = datetime.now(MOSCOW_TIMEZONE).date()
    await message.answer(
        "📅 <b>Выберите дату</b>\n\n"
        "Можно выбрать сегодняшний день или прошедшую дату.",
        reply_markup=appointment_date_calendar_keyboard(
            year=today.year,
            month=today.month,
            today=today,
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "past:noop")
async def calendar_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.in_({"past:cancel", "daily:cancel"}))
async def cancel_daily_entry_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Добавление дневного итога отменено.")
    await callback.answer()


@router.callback_query(F.data == "daily:done")
async def finish_daily_entry_handler(
    callback: CallbackQuery,
    state: FSMContext,
    is_admin: bool,
) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Готово. Выберите следующее действие:",
            reply_markup=get_main_keyboard(is_admin),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("past:nav:"))
async def navigate_calendar_handler(callback: CallbackQuery) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await callback.answer("Некорректный месяц.", show_alert=True)
        return

    year = int(parts[2])
    month = int(parts[3])
    today = datetime.now(MOSCOW_TIMEZONE).date()

    if year < 2000 or month < 1 or month > 12:
        await callback.answer("Дата вне допустимого диапазона.", show_alert=True)
        return

    if date(year, month, 1) > date(today.year, today.month, 1):
        await callback.answer("Будущую дату выбрать нельзя.", show_alert=True)
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


@router.callback_query(F.data.startswith("past:day:"))
async def select_calendar_day_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 5 or not all(part.isdigit() for part in parts[2:5]):
        await callback.answer("Некорректная дата.", show_alert=True)
        return

    try:
        selected_date = date(int(parts[2]), int(parts[3]), int(parts[4]))
    except ValueError:
        await callback.answer("Некорректная дата.", show_alert=True)
        return

    if selected_date > datetime.now(MOSCOW_TIMEZONE).date():
        await callback.answer("Будущую дату выбрать нельзя.", show_alert=True)
        return

    await state.clear()
    if callback.message:
        await show_daily_clinics(callback.message, selected_date, edit_message=True)
    await callback.answer()


@router.callback_query(F.data.startswith("daily:clinics:"))
async def reopen_daily_clinics_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    selected_date = parse_iso_date(callback.data.split(":", maxsplit=2)[-1])
    if selected_date is None:
        await callback.answer("Некорректная дата.", show_alert=True)
        return

    await state.clear()
    if callback.message:
        await show_daily_clinics(callback.message, selected_date, edit_message=True)
    await callback.answer()


@router.callback_query(F.data.startswith("daily:clinic:"))
async def select_daily_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4 or not parts[3].isdigit():
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    selected_date = parse_iso_date(parts[2])
    if selected_date is None:
        await callback.answer("Некорректная дата.", show_alert=True)
        return

    clinic_id = int(parts[3])
    clinic = await get_clinic_by_id(clinic_id)
    if clinic is None:
        await callback.answer("Поликлиника не найдена.", show_alert=True)
        return

    specialties = await get_specialties(clinic_id)
    if not specialties:
        await callback.answer(
            "В этой поликлинике нет активных специальностей.",
            show_alert=True,
        )
        return

    _, clinic_name, _, _ = clinic
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            "📋 <b>Дневной итог</b>\n\n"
            f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
            f"Поликлиника: <b>{escape(clinic_name)}</b>\n\n"
            "🩺 Выберите специальность:",
            reply_markup=daily_specialties_keyboard(
                selected_date,
                clinic_id,
                specialties,
            ),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("daily:specialty:"))
async def select_daily_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if (
        len(parts) != 5
        or not parts[3].isdigit()
        or not parts[4].isdigit()
    ):
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    selected_date = parse_iso_date(parts[2])
    if selected_date is None:
        await callback.answer("Некорректная дата.", show_alert=True)
        return

    clinic_id = int(parts[3])
    specialty_id = int(parts[4])
    clinic = await get_clinic_by_id(clinic_id)
    specialty = await get_specialty_by_id(specialty_id)

    if clinic is None or specialty is None:
        await callback.answer(
            "Поликлиника или специальность не найдена.",
            show_alert=True,
        )
        return

    (
        _,
        specialty_clinic_id,
        specialty_name,
        primary_price,
        secondary_price,
    ) = specialty

    if specialty_clinic_id != clinic_id:
        await callback.answer(
            "Специальность не относится к этой поликлинике.",
            show_alert=True,
        )
        return

    _, clinic_name, _, _ = clinic
    existing = await get_daily_entry_by_key(
        work_date=selected_date.isoformat(),
        specialty_id=specialty_id,
    )

    await state.clear()
    await state.update_data(
        selected_date=selected_date.isoformat(),
        clinic_id=clinic_id,
        clinic_name=clinic_name,
        specialty_id=specialty_id,
        specialty_name=specialty_name,
        primary_price=primary_price,
        secondary_price=secondary_price,
        existing=existing is not None,
    )
    await state.set_state(DailyEntry.primary_count)

    existing_text = ""
    if existing is not None:
        existing_text = (
            "\n\n⚠️ За эту дату уже сохранено:\n"
            f"Первичных: {int(existing[1])}\n"
            f"Повторных: {int(existing[2])}\n"
            "Новые значения заменят текущую запись."
        )

    if callback.message:
        await callback.message.answer(
            "📋 <b>Дневной итог</b>\n\n"
            f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
            f"🏥 {escape(clinic_name)}\n"
            f"🩺 {escape(specialty_name)}"
            f"{existing_text}\n\n"
            "Введите количество первичных приёмов.\n"
            "Если их не было — введите 0.",
            reply_markup=count_keyboard,
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(DailyEntry.primary_count)
async def primary_count_handler(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите количество цифрами.")
        return

    primary_count = parse_count(message.text)
    if primary_count is None:
        await message.answer("Введите целое число от 0 до 1000.")
        return

    await state.update_data(primary_count=primary_count)
    await state.set_state(DailyEntry.secondary_count)
    await message.answer(
        "Введите количество повторных приёмов.\n"
        "Если их не было — введите 0.",
        reply_markup=count_keyboard,
    )


@router.message(DailyEntry.secondary_count)
async def secondary_count_handler(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите количество цифрами.")
        return

    secondary_count = parse_count(message.text)
    if secondary_count is None:
        await message.answer("Введите целое число от 0 до 1000.")
        return

    data = await state.get_data()
    primary_count = int(data["primary_count"])
    if primary_count == 0 and secondary_count == 0:
        await message.answer(
            "Нельзя сохранить нулевую запись.\n"
            "Введите количество повторных приёмов ещё раз."
        )
        return

    primary_price = int(data["primary_price"])
    secondary_price = int(data["secondary_price"])
    primary_amount = primary_count * primary_price
    secondary_amount = secondary_count * secondary_price
    total_amount = primary_amount + secondary_amount

    await state.update_data(secondary_count=secondary_count)
    await state.set_state(DailyEntry.confirmation)

    selected_date = date.fromisoformat(str(data["selected_date"]))
    action_text = (
        "Текущая запись будет заменена."
        if bool(data["existing"])
        else "Будет создана новая дневная запись."
    )

    await message.answer(
        "Проверьте дневной итог:\n\n"
        f"📅 <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
        f"🏥 {escape(str(data['clinic_name']))}\n"
        f"🩺 {escape(str(data['specialty_name']))}\n\n"
        f"Первичных: {primary_count} × "
        f"{format_price(primary_price)} ₽ = "
        f"{format_price(primary_amount)} ₽\n"
        f"Повторных: {secondary_count} × "
        f"{format_price(secondary_price)} ₽ = "
        f"{format_price(secondary_amount)} ₽\n\n"
        f"💰 <b>Итого: {format_price(total_amount)} ₽</b>\n\n"
        f"{action_text}",
        reply_markup=daily_confirmation_keyboard,
        parse_mode="HTML",
    )


@router.callback_query(DailyEntry.confirmation, F.data == "daily:save")
async def save_daily_entry_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    result = await save_daily_entry(
        work_date=str(data["selected_date"]),
        specialty_id=int(data["specialty_id"]),
        primary_count=int(data["primary_count"]),
        secondary_count=int(data["secondary_count"]),
    )

    if result is None:
        await callback.answer("Не удалось сохранить дневной итог.", show_alert=True)
        return

    (
        status,
        clinic_name,
        specialty_name,
        primary_count,
        secondary_count,
        primary_amount,
        secondary_amount,
    ) = result

    selected_date = date.fromisoformat(str(data["selected_date"]))
    total_amount = primary_amount + secondary_amount
    await state.clear()
    status_text = "обновлён" if status == "updated" else "добавлен"

    if callback.message:
        await callback.message.edit_text(
            f"✅ <b>Дневной итог {status_text}</b>\n\n"
            f"📅 {selected_date.strftime('%d.%m.%Y')}\n"
            f"🏥 {escape(clinic_name)}\n"
            f"🩺 {escape(specialty_name)}\n\n"
            f"Первичных: {primary_count} — "
            f"{format_price(primary_amount)} ₽\n"
            f"Повторных: {secondary_count} — "
            f"{format_price(secondary_amount)} ₽\n\n"
            f"💰 <b>Итого: {format_price(total_amount)} ₽</b>",
            reply_markup=daily_result_keyboard(selected_date),
            parse_mode="HTML",
        )
    await callback.answer("Дневной итог сохранён")


@router.callback_query(F.data.startswith("appointment:"))
@router.callback_query(F.data.startswith("past:clinic:"))
@router.callback_query(F.data.startswith("past:specialty:"))
@router.callback_query(F.data.startswith("past:type:"))
@router.callback_query(F.data.startswith("past:confirm:"))
async def old_appointment_button_handler(callback: CallbackQuery) -> None:
    await callback.answer(
        "Эта старая кнопка больше не действует.\n"
        "Начните добавление заново из главного меню.",
        show_alert=True,
    )
