from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database.db import (
    delete_appointment,
    delete_daily_entry,
    get_last_appointment,
    get_last_daily_entry,
)
from keyboards.history import delete_record_keyboard
from keyboards.main import get_main_keyboard


router = Router()
MOSCOW_TIMEZONE = timezone(timedelta(hours=3))


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


def format_created_at(created_at: str) -> str:
    item_time = datetime.fromisoformat(created_at)
    local_time = item_time.astimezone(MOSCOW_TIMEZONE)
    return local_time.strftime("%d.%m.%Y в %H:%M")


@router.message(F.text.in_({"🙀 Последняя запись", "🙀 Последний приём"}))
async def show_last_record_handler(
    message: Message,
    is_admin: bool,
) -> None:
    daily_entry = await get_last_daily_entry()

    if daily_entry is not None:
        (
            entry_id,
            clinic_name,
            specialty_name,
            work_date,
            primary_count,
            secondary_count,
            primary_amount,
            secondary_amount,
            updated_at,
        ) = daily_entry

        total_amount = primary_amount + secondary_amount
        display_date = datetime.fromisoformat(work_date).strftime("%d.%m.%Y")

        await message.answer(
            "↩️ <b>Последняя дневная запись</b>\n\n"
            f"📅 {display_date}\n"
            f"🏥 {escape(clinic_name)}\n"
            f"🩺 {escape(specialty_name)}\n\n"
            f"Первичных: {primary_count} — "
            f"{format_price(primary_amount)} ₽\n"
            f"Повторных: {secondary_count} — "
            f"{format_price(secondary_amount)} ₽\n\n"
            f"💰 <b>Итого: {format_price(total_amount)} ₽</b>\n"
            f"Сохранено: {format_created_at(updated_at)}\n\n"
            "Удалить эту дневную запись?",
            reply_markup=delete_record_keyboard("daily", entry_id),
            parse_mode="HTML",
        )
        return

    appointment = await get_last_appointment()

    if appointment is None:
        await message.answer(
            "Записей пока нет.",
            reply_markup=get_main_keyboard(is_admin),
        )
        return

    (
        appointment_id,
        clinic_name,
        specialty_name,
        visit_type,
        amount,
        created_at,
    ) = appointment
    visit_type_name = "Первичный" if visit_type == "primary" else "Повторный"

    await message.answer(
        "↩️ <b>Последний старый приём</b>\n\n"
        f"🏥 {escape(clinic_name)}\n"
        f"🩺 {escape(specialty_name)}\n"
        f"Тип: {visit_type_name}\n"
        f"Сумма: {format_price(amount)} ₽\n"
        f"Дата: {format_created_at(created_at)}\n\n"
        "Удалить эту запись?",
        reply_markup=delete_record_keyboard("appointment", appointment_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "history:keep")
async def keep_record_handler(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text("✅ Запись оставлена без изменений.")
    await callback.answer()


@router.callback_query(F.data.startswith("history:delete:"))
async def delete_record_handler(callback: CallbackQuery) -> None:
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4 or not parts[3].isdigit():
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    record_type = parts[2]
    record_id = int(parts[3])

    if record_type == "daily":
        deleted = await delete_daily_entry(record_id)
    elif record_type == "appointment":
        deleted = await delete_appointment(record_id)
    else:
        await callback.answer("Неизвестный тип записи.", show_alert=True)
        return

    if not deleted:
        await callback.answer(
            "Запись уже удалена или не найдена.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "🗑 <b>Запись удалена.</b>\n\nСтатистика обновлена.",
            parse_mode="HTML",
        )
    await callback.answer("Запись удалена")
