from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database.db import delete_appointment, get_last_appointment
from keyboards.history import delete_appointment_keyboard
from keyboards.main import get_main_keyboard


router = Router()

MOSCOW_TIMEZONE = timezone(timedelta(hours=3))


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


def format_created_at(created_at: str) -> str:
    appointment_time = datetime.fromisoformat(created_at)
    local_time = appointment_time.astimezone(MOSCOW_TIMEZONE)

    return local_time.strftime("%d.%m.%Y в %H:%M")


@router.message(F.text == "🙀 Последний приём")
async def show_last_appointment_handler(
    message: Message,
    is_admin: bool,
) -> None:
    appointment = await get_last_appointment()

    if appointment is None:
        await message.answer(
            "Записей о приёмах пока нет.",
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

    visit_type_name = (
        "Первичный"
        if visit_type == "primary"
        else "Повторный"
    )

    await message.answer(
        "↩️ <b>Последний приём</b>\n\n"
        f"🏥 {escape(clinic_name)}\n"
        f"🩺 {escape(specialty_name)}\n"
        f"Тип: {visit_type_name}\n"
        f"Сумма: {format_price(amount)} ₽\n"
        f"Дата: {format_created_at(created_at)}\n\n"
        "Удалить эту запись?",
        reply_markup=delete_appointment_keyboard(appointment_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "history:keep")
async def keep_appointment_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message:
        await callback.message.edit_text(
            "✅ Запись оставлена без изменений."
        )

    await callback.answer()


@router.callback_query(F.data.startswith("history:delete:"))
async def delete_appointment_handler(
    callback: CallbackQuery,
) -> None:
    if not callback.data:
        await callback.answer()
        return

    appointment_id_text = callback.data.rsplit(":", maxsplit=1)[-1]

    if not appointment_id_text.isdigit():
        await callback.answer(
            "Некорректный номер записи.",
            show_alert=True,
        )
        return

    appointment_id = int(appointment_id_text)
    deleted = await delete_appointment(appointment_id)

    if not deleted:
        await callback.answer(
            "Запись уже удалена или не найдена.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "🗑 <b>Последний приём удалён.</b>\n\n"
            "Статистика обновлена.",
            parse_mode="HTML",
        )

    await callback.answer("Запись удалена")
