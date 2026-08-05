from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database.db import (
    add_appointment,
    get_clinic_by_id,
    get_clinics,
)
from keyboards.appointments import (
    appointment_clinics_keyboard,
    appointment_type_keyboard,
)
from keyboards.main import get_main_keyboard


router = Router()


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


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


@router.message(F.text == "🐾 Добавить приём")
async def start_add_appointment_handler(
    message: Message,
    is_admin: bool,
) -> None:
    await show_clinic_selection(
        message=message,
        is_admin=is_admin,
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
            f"🏥 <b>{name}</b>\n\n"
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
            f"🏥 {clinic_name}\n"
            f"Тип: {visit_type_name}\n"
            f"Сумма: {format_price(amount)} ₽",
            parse_mode="HTML",
        )

    await callback.answer("Приём сохранён")
