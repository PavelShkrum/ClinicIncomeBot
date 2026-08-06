from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import (
    add_clinic_with_specialty,
    archive_clinic,
    get_clinic_by_id,
    get_clinics,
    get_specialties,
    rename_clinic,
)
from keyboards.clinics import (
    add_clinic_confirmation_keyboard,
    cancel_keyboard,
    clinics_menu_keyboard,
    delete_clinic_confirmation_keyboard,
    rename_clinic_confirmation_keyboard,
)
from keyboards.main import get_main_keyboard
from states.clinic import AddClinic, RenameClinic


router = Router()


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ")


def parse_price(text: str) -> int | None:
    normalized_text = (
        text.replace(" ", "")
        .replace("\u00a0", "")
        .replace("₽", "")
        .strip()
    )

    if not normalized_text.isdigit():
        return None

    price = int(normalized_text)

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


async def build_clinics_overview(
) -> tuple[str, list[tuple[int, str, int, int]]]:
    clinics = await get_clinics()

    if not clinics:
        return (
            "Поликлиники пока не добавлены.\n\n"
            "Нажмите кнопку ниже, чтобы добавить первую.",
            clinics,
        )

    lines = ["🏥 <b>Поликлиники и цены</b>"]

    for clinic_id, clinic_name, _, _ in clinics:
        lines.append(f"\n🏥 <b>{escape(clinic_name)}</b>")

        specialties = await get_specialties(clinic_id)

        if not specialties:
            lines.append("Специальности пока не добавлены.")
            continue

        for _, specialty_name, primary_price, secondary_price in specialties:
            lines.append(
                "\n"
                f"🩺 <b>{escape(specialty_name)}</b>\n"
                f"Первичный: {format_price(primary_price)} ₽\n"
                f"Повторный: {format_price(secondary_price)} ₽"
            )

    return "\n".join(lines), clinics


async def show_clinics_overview(
    message: Message,
    edit_message: bool = False,
) -> None:
    text, clinics = await build_clinics_overview()
    keyboard = clinics_menu_keyboard(clinics)

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


@router.message(F.text == "😼 Поликлиники и цены")
async def show_clinics_handler(message: Message) -> None:
    await show_clinics_overview(message)


@router.callback_query(F.data == "clinic:add")
async def start_add_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(AddClinic.name)

    if callback.message:
        await callback.message.answer(
            "🏥 <b>Добавление поликлиники</b>\n\n"
            "Введите название поликлиники.\n\n"
            "Например: Поликлиника №5",
            reply_markup=cancel_keyboard,
            parse_mode="HTML",
        )

    await callback.answer()


@router.message(AddClinic.name)
async def add_clinic_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите название текстом.")
        return

    clinic_name = validate_name(message.text)

    if clinic_name is None:
        await message.answer(
            "Название должно содержать от 2 до 60 символов."
        )
        return

    await state.update_data(clinic_name=clinic_name)
    await state.set_state(AddClinic.specialty_name)

    await message.answer(
        "🩺 Введите первую специальность в этой поликлинике.\n\n"
        "Например: Терапевт"
    )


@router.message(AddClinic.specialty_name)
async def add_clinic_specialty_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите специальность текстом.")
        return

    specialty_name = validate_name(message.text)

    if specialty_name is None:
        await message.answer(
            "Название специальности должно содержать "
            "от 2 до 60 символов."
        )
        return

    await state.update_data(specialty_name=specialty_name)
    await state.set_state(AddClinic.primary_price)

    await message.answer(
        "Введите цену первичного приёма в рублях.\n\n"
        "Например: 2500"
    )


@router.message(AddClinic.primary_price)
async def add_clinic_primary_price_handler(
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
    await state.set_state(AddClinic.secondary_price)

    await message.answer(
        "Введите цену повторного приёма в рублях.\n\n"
        "Например: 1800"
    )


@router.message(AddClinic.secondary_price)
async def add_clinic_secondary_price_handler(
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
    await state.set_state(AddClinic.confirmation)

    data = await state.get_data()

    await message.answer(
        "Проверьте данные:\n\n"
        f"🏥 <b>{escape(str(data['clinic_name']))}</b>\n\n"
        f"🩺 <b>{escape(str(data['specialty_name']))}</b>\n"
        f"Первичный: "
        f"{format_price(int(data['primary_price']))} ₽\n"
        f"Повторный: {format_price(secondary_price)} ₽\n\n"
        "Сохранить поликлинику?",
        reply_markup=add_clinic_confirmation_keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    AddClinic.confirmation,
    F.data == "clinic:add:save",
)
async def save_added_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    clinic_name = str(data["clinic_name"])
    specialty_name = str(data["specialty_name"])
    primary_price = int(data["primary_price"])
    secondary_price = int(data["secondary_price"])

    result = await add_clinic_with_specialty(
        clinic_name=clinic_name,
        specialty_name=specialty_name,
        primary_price=primary_price,
        secondary_price=secondary_price,
    )

    if result == "duplicate_clinic":
        await callback.answer(
            "Поликлиника с таким названием уже существует.",
            show_alert=True,
        )
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Поликлиника добавлена</b>\n\n"
            f"🏥 {escape(clinic_name)}\n\n"
            f"🩺 {escape(specialty_name)}\n"
            f"Первичный: {format_price(primary_price)} ₽\n"
            f"Повторный: {format_price(secondary_price)} ₽",
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer("Поликлиника сохранена")


@router.callback_query(
    AddClinic.confirmation,
    F.data == "clinic:add:cancel",
)
async def cancel_added_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Добавление поликлиники отменено."
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer()


@router.callback_query(
    F.data.regexp(r"^clinic:(rename|edit):\d+$")
)
async def start_rename_clinic_handler(
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
        old_name=clinic_name,
    )
    await state.set_state(RenameClinic.name)

    if callback.message:
        await callback.message.answer(
            "✏️ <b>Изменение названия поликлиники</b>\n\n"
            f"Сейчас: <b>{escape(clinic_name)}</b>\n\n"
            "Введите новое название:",
            reply_markup=cancel_keyboard,
            parse_mode="HTML",
        )

    await callback.answer()


@router.message(RenameClinic.name)
async def rename_clinic_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите название текстом.")
        return

    new_name = validate_name(message.text)

    if new_name is None:
        await message.answer(
            "Название должно содержать от 2 до 60 символов."
        )
        return

    await state.update_data(new_name=new_name)
    await state.set_state(RenameClinic.confirmation)

    data = await state.get_data()

    await message.answer(
        "Проверьте изменение:\n\n"
        f"Было: <b>{escape(str(data['old_name']))}</b>\n"
        f"Станет: <b>{escape(new_name)}</b>\n\n"
        "Сохранить новое название?",
        reply_markup=rename_clinic_confirmation_keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    RenameClinic.confirmation,
    F.data == "clinic:rename:save",
)
async def save_renamed_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    clinic_id = int(data["clinic_id"])
    new_name = str(data["new_name"])

    result = await rename_clinic(
        clinic_id=clinic_id,
        new_name=new_name,
    )

    if result == "duplicate_name":
        await callback.answer(
            "Поликлиника с таким названием уже существует.",
            show_alert=True,
        )
        return

    if result == "not_found":
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "✅ Название поликлиники изменено.\n\n"
            f"🏥 <b>{escape(new_name)}</b>",
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer("Название сохранено")


@router.callback_query(
    RenameClinic.confirmation,
    F.data == "clinic:rename:cancel",
)
async def cancel_renamed_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Изменение названия отменено."
        )

    await callback.answer()


@router.callback_query(F.data.regexp(r"^clinic:prices:\d+$"))
async def old_prices_button_handler(
    callback: CallbackQuery,
) -> None:
    await callback.answer(
        "Цены теперь настраиваются отдельно "
        "в разделе специальностей.",
        show_alert=True,
    )


@router.callback_query(F.data.regexp(r"^clinic:delete:\d+$"))
async def request_delete_clinic_handler(
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

    _, name, _, _ = clinic
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "🗑 <b>Удаление поликлиники</b>\n\n"
            f"🏥 <b>{escape(name)}</b>\n\n"
            "Поликлиника и её специальности исчезнут "
            "из активного списка.\n\n"
            "Удалить поликлинику?",
            reply_markup=delete_clinic_confirmation_keyboard(
                clinic_id
            ),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(
    F.data.regexp(r"^clinic:delete:confirm:\d+$")
)
async def confirm_delete_clinic_handler(
    callback: CallbackQuery,
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
            "Поликлиника уже удалена.",
            show_alert=True,
        )
        return

    _, name, _, _ = clinic
    archived = await archive_clinic(clinic_id)

    if not archived:
        await callback.answer(
            "Не удалось удалить поликлинику.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "✅ Поликлиника удалена из активных.\n\n"
            f"🏥 <b>{escape(name)}</b>",
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer("Поликлиника удалена")


@router.callback_query(F.data == "clinic:delete:cancel")
async def cancel_delete_clinic_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Удаление поликлиники отменено."
        )

    await callback.answer()


@router.message(F.text == "❌ Отмена")
async def cancel_handler(
    message: Message,
    state: FSMContext,
) -> None:
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "Сейчас нечего отменять.",
            reply_markup=get_main_keyboard(is_admin=True),
        )
        return

    await state.clear()

    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_keyboard(is_admin=True),
    )
