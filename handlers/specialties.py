from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import (
    add_specialty,
    archive_specialty,
    get_clinic_by_id,
    get_clinics,
    get_specialties,
    get_specialty_by_id,
    update_specialty,
)
from keyboards.clinics import cancel_keyboard, clinics_menu_keyboard
from keyboards.main import get_main_keyboard
from keyboards.specialties import (
    delete_specialty_confirmation_keyboard,
    specialties_menu_keyboard,
    specialty_confirmation_keyboard,
    specialty_management_keyboard,
)
from states.specialty import AddSpecialty, EditSpecialty


router = Router()


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


def parse_price(text: str) -> int | None:
    normalized = (
        text.replace(" ", "")
        .replace("\u00a0", "")
        .replace("₽", "")
        .strip()
    )

    if not normalized.isdigit():
        return None

    price = int(normalized)

    if price <= 0:
        return None

    return price


def validate_name(text: str) -> str | None:
    name = text.strip()

    if len(name) < 2 or len(name) > 60:
        return None

    return name


def parse_last_id(callback_data: str | None) -> int | None:
    if not callback_data:
        return None

    value = callback_data.rsplit(":", maxsplit=1)[-1]

    if not value.isdigit():
        return None

    return int(value)


async def show_specialties(
    message: Message,
    clinic_id: int,
    edit_message: bool,
) -> bool:
    clinic = await get_clinic_by_id(clinic_id)

    if clinic is None:
        return False

    _, clinic_name, _, _ = clinic
    specialties = await get_specialties(clinic_id)

    lines = [
        "🩺 <b>Специальности и цены</b>",
        f"🏥 <b>{escape(clinic_name)}</b>",
    ]

    if not specialties:
        lines.append("\nСпециальности пока не добавлены.")
    else:
        for _, name, primary_price, secondary_price in specialties:
            lines.append(
                "\n"
                f"<b>{escape(name)}</b>\n"
                f"Первичный: {format_price(primary_price)} ₽\n"
                f"Повторный: {format_price(secondary_price)} ₽"
            )

    keyboard = specialties_menu_keyboard(
        clinic_id=clinic_id,
        specialties=specialties,
    )

    if edit_message:
        await message.edit_text(
            "\n".join(lines),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "\n".join(lines),
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    return True


@router.callback_query(F.data.regexp(r"^specialty:list:\d+$"))
async def specialties_list_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    clinic_id = parse_last_id(callback.data)

    if clinic_id is None:
        await callback.answer(
            "Некорректная поликлиника.",
            show_alert=True,
        )
        return

    await state.clear()

    if callback.message:
        found = await show_specialties(
            message=callback.message,
            clinic_id=clinic_id,
            edit_message=True,
        )

        if not found:
            await callback.answer(
                "Поликлиника не найдена.",
                show_alert=True,
            )
            return

    await callback.answer()


@router.callback_query(F.data == "specialty:back")
async def specialties_back_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    clinics = await get_clinics()

    if callback.message:
        if not clinics:
            text = (
                "Поликлиники пока не добавлены.\n\n"
                "Нажмите кнопку ниже, чтобы добавить первую."
            )
        else:
            lines = ["🏥 <b>Поликлиники и цены</b>\n"]

            for _, name, primary_price, secondary_price in clinics:
                lines.append(
                    f"<b>{escape(name)}</b>\n"
                    f"Первичный: {format_price(primary_price)} ₽\n"
                    f"Вторичный: {format_price(secondary_price)} ₽"
                )

            text = "\n\n".join(lines)

        await callback.message.edit_text(
            text,
            reply_markup=clinics_menu_keyboard(clinics),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data.regexp(r"^specialty:add:\d+$"))
async def start_add_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    clinic_id = parse_last_id(callback.data)

    if clinic_id is None:
        await callback.answer(
            "Некорректная поликлиника.",
            show_alert=True,
        )
        return

    clinic = await get_clinic_by_id(clinic_id)

    if clinic is None:
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    _, clinic_name, _, _ = clinic

    await state.clear()
    await state.update_data(
        clinic_id=clinic_id,
        clinic_name=clinic_name,
    )
    await state.set_state(AddSpecialty.name)

    if callback.message:
        await callback.message.answer(
            "➕ <b>Добавление специальности</b>\n\n"
            f"Поликлиника: <b>{escape(clinic_name)}</b>\n\n"
            "Введите название специальности.\n"
            "Например: Терапевт",
            reply_markup=cancel_keyboard,
            parse_mode="HTML",
        )

    await callback.answer()


@router.message(AddSpecialty.name)
async def add_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите название текстом.")
        return

    name = validate_name(message.text)

    if name is None:
        await message.answer(
            "Название должно содержать от 2 до 60 символов."
        )
        return

    await state.update_data(name=name)
    await state.set_state(AddSpecialty.primary_price)

    await message.answer(
        "Введите цену первичного приёма в рублях.\n\n"
        "Например: 2500"
    )


@router.message(AddSpecialty.primary_price)
async def add_primary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите цену цифрами.")
        return

    primary_price = parse_price(message.text)

    if primary_price is None:
        await message.answer(
            "Введите целое положительное число, например: 2500"
        )
        return

    await state.update_data(primary_price=primary_price)
    await state.set_state(AddSpecialty.secondary_price)

    await message.answer(
        "Введите цену повторного приёма в рублях.\n\n"
        "Например: 1800"
    )


@router.message(AddSpecialty.secondary_price)
async def add_secondary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите цену цифрами.")
        return

    secondary_price = parse_price(message.text)

    if secondary_price is None:
        await message.answer(
            "Введите целое положительное число, например: 1800"
        )
        return

    await state.update_data(secondary_price=secondary_price)
    await state.set_state(AddSpecialty.confirmation)

    data = await state.get_data()

    await message.answer(
        "Проверьте данные:\n\n"
        f"🏥 {escape(str(data['clinic_name']))}\n"
        f"🩺 <b>{escape(str(data['name']))}</b>\n"
        f"Первичный: {format_price(int(data['primary_price']))} ₽\n"
        f"Повторный: {format_price(secondary_price)} ₽\n\n"
        "Сохранить специальность?",
        reply_markup=specialty_confirmation_keyboard("add"),
        parse_mode="HTML",
    )


@router.callback_query(
    AddSpecialty.confirmation,
    F.data == "specialty:add:save",
)
async def save_added_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    clinic_id = int(data["clinic_id"])
    name = str(data["name"])
    primary_price = int(data["primary_price"])
    secondary_price = int(data["secondary_price"])

    result = await add_specialty(
        clinic_id=clinic_id,
        name=name,
        primary_price=primary_price,
        secondary_price=secondary_price,
    )

    if result == "duplicate_name":
        await callback.answer(
            "Такая специальность уже существует.",
            show_alert=True,
        )
        return

    if result == "clinic_not_found":
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Специальность добавлена</b>\n\n"
            f"🩺 {escape(name)}\n"
            f"Первичный: {format_price(primary_price)} ₽\n"
            f"Повторный: {format_price(secondary_price)} ₽",
            parse_mode="HTML",
        )

        await show_specialties(
            message=callback.message,
            clinic_id=clinic_id,
            edit_message=False,
        )

        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer("Специальность сохранена")


@router.callback_query(
    AddSpecialty.confirmation,
    F.data == "specialty:add:cancel",
)
async def cancel_added_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    clinic_id = int(data["clinic_id"])
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Добавление специальности отменено."
        )
        await show_specialties(
            message=callback.message,
            clinic_id=clinic_id,
            edit_message=False,
        )

    await callback.answer()


@router.callback_query(F.data.regexp(r"^specialty:manage:\d+$"))
async def manage_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    specialty_id = parse_last_id(callback.data)

    if specialty_id is None:
        await callback.answer(
            "Некорректная специальность.",
            show_alert=True,
        )
        return

    specialty = await get_specialty_by_id(specialty_id)

    if specialty is None:
        await callback.answer(
            "Специальность не найдена.",
            show_alert=True,
        )
        return

    _, clinic_id, name, primary_price, secondary_price = specialty
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "⚙️ <b>Управление специальностью</b>\n\n"
            f"🩺 <b>{escape(name)}</b>\n"
            f"Первичный: {format_price(primary_price)} ₽\n"
            f"Повторный: {format_price(secondary_price)} ₽",
            reply_markup=specialty_management_keyboard(
                specialty_id=specialty_id,
                clinic_id=clinic_id,
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data.regexp(r"^specialty:edit:\d+$"))
async def start_edit_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    specialty_id = parse_last_id(callback.data)

    if specialty_id is None:
        await callback.answer(
            "Некорректная специальность.",
            show_alert=True,
        )
        return

    specialty = await get_specialty_by_id(specialty_id)

    if specialty is None:
        await callback.answer(
            "Специальность не найдена.",
            show_alert=True,
        )
        return

    _, clinic_id, name, primary_price, secondary_price = specialty

    await state.clear()
    await state.update_data(
        specialty_id=specialty_id,
        clinic_id=clinic_id,
        old_name=name,
        old_primary_price=primary_price,
        old_secondary_price=secondary_price,
    )
    await state.set_state(EditSpecialty.name)

    if callback.message:
        await callback.message.answer(
            "✏️ <b>Изменение специальности</b>\n\n"
            f"Текущее название: <b>{escape(name)}</b>\n\n"
            "Введите новое название:",
            reply_markup=cancel_keyboard,
            parse_mode="HTML",
        )

    await callback.answer()


@router.message(EditSpecialty.name)
async def edit_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите название текстом.")
        return

    name = validate_name(message.text)

    if name is None:
        await message.answer(
            "Название должно содержать от 2 до 60 символов."
        )
        return

    await state.update_data(new_name=name)
    await state.set_state(EditSpecialty.primary_price)

    data = await state.get_data()

    await message.answer(
        "Введите новую цену первичного приёма.\n"
        f"Сейчас: {format_price(int(data['old_primary_price']))} ₽"
    )


@router.message(EditSpecialty.primary_price)
async def edit_primary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите цену цифрами.")
        return

    primary_price = parse_price(message.text)

    if primary_price is None:
        await message.answer(
            "Введите целое положительное число, например: 2500"
        )
        return

    await state.update_data(new_primary_price=primary_price)
    await state.set_state(EditSpecialty.secondary_price)

    data = await state.get_data()

    await message.answer(
        "Введите новую цену повторного приёма.\n"
        f"Сейчас: {format_price(int(data['old_secondary_price']))} ₽"
    )


@router.message(EditSpecialty.secondary_price)
async def edit_secondary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите цену цифрами.")
        return

    secondary_price = parse_price(message.text)

    if secondary_price is None:
        await message.answer(
            "Введите целое положительное число, например: 1800"
        )
        return

    await state.update_data(new_secondary_price=secondary_price)
    await state.set_state(EditSpecialty.confirmation)

    data = await state.get_data()

    await message.answer(
        "Проверьте изменения:\n\n"
        "<b>Было</b>\n"
        f"🩺 {escape(str(data['old_name']))}\n"
        f"Первичный: {format_price(int(data['old_primary_price']))} ₽\n"
        f"Повторный: {format_price(int(data['old_secondary_price']))} ₽\n\n"
        "<b>Станет</b>\n"
        f"🩺 {escape(str(data['new_name']))}\n"
        f"Первичный: {format_price(int(data['new_primary_price']))} ₽\n"
        f"Повторный: {format_price(secondary_price)} ₽\n\n"
        "Сохранить изменения?",
        reply_markup=specialty_confirmation_keyboard("edit"),
        parse_mode="HTML",
    )


@router.callback_query(
    EditSpecialty.confirmation,
    F.data == "specialty:edit:save",
)
async def save_edited_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    specialty_id = int(data["specialty_id"])
    clinic_id = int(data["clinic_id"])
    name = str(data["new_name"])
    primary_price = int(data["new_primary_price"])
    secondary_price = int(data["new_secondary_price"])

    result = await update_specialty(
        specialty_id=specialty_id,
        name=name,
        primary_price=primary_price,
        secondary_price=secondary_price,
    )

    if result == "duplicate_name":
        await callback.answer(
            "Такая специальность уже существует.",
            show_alert=True,
        )
        return

    if result == "not_found":
        await callback.answer(
            "Специальность не найдена.",
            show_alert=True,
        )
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Специальность обновлена</b>\n\n"
            f"🩺 {escape(name)}\n"
            f"Первичный: {format_price(primary_price)} ₽\n"
            f"Повторный: {format_price(secondary_price)} ₽",
            parse_mode="HTML",
        )

        await show_specialties(
            message=callback.message,
            clinic_id=clinic_id,
            edit_message=False,
        )

        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer("Изменения сохранены")


@router.callback_query(
    EditSpecialty.confirmation,
    F.data == "specialty:edit:cancel",
)
async def cancel_edited_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    clinic_id = int(data["clinic_id"])
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Изменение специальности отменено."
        )
        await show_specialties(
            message=callback.message,
            clinic_id=clinic_id,
            edit_message=False,
        )

    await callback.answer()


@router.callback_query(F.data.regexp(r"^specialty:delete:\d+$"))
async def request_delete_specialty_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    specialty_id = parse_last_id(callback.data)

    if specialty_id is None:
        await callback.answer(
            "Некорректная специальность.",
            show_alert=True,
        )
        return

    specialty = await get_specialty_by_id(specialty_id)

    if specialty is None:
        await callback.answer(
            "Специальность не найдена.",
            show_alert=True,
        )
        return

    _, clinic_id, name, _, _ = specialty
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "🗑 <b>Удаление специальности</b>\n\n"
            f"🩺 <b>{escape(name)}</b>\n\n"
            "Специальность исчезнет из активного списка.\n"
            "Удалить её?",
            reply_markup=delete_specialty_confirmation_keyboard(
                specialty_id=specialty_id,
                clinic_id=clinic_id,
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(
    F.data.regexp(r"^specialty:delete:confirm:\d+$")
)
async def confirm_delete_specialty_handler(
    callback: CallbackQuery,
) -> None:
    specialty_id = parse_last_id(callback.data)

    if specialty_id is None:
        await callback.answer(
            "Некорректная специальность.",
            show_alert=True,
        )
        return

    specialty = await get_specialty_by_id(specialty_id)

    if specialty is None:
        await callback.answer(
            "Специальность уже удалена.",
            show_alert=True,
        )
        return

    _, clinic_id, name, _, _ = specialty
    archived = await archive_specialty(specialty_id)

    if not archived:
        await callback.answer(
            "Не удалось удалить специальность.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "✅ Специальность удалена.\n\n"
            f"🩺 <b>{escape(name)}</b>",
            parse_mode="HTML",
        )

        await show_specialties(
            message=callback.message,
            clinic_id=clinic_id,
            edit_message=False,
        )

    await callback.answer("Специальность удалена")
