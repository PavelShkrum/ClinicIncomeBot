from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import (
    add_clinic,
    get_clinic_by_id,
    get_clinics,
    update_clinic,
)
from keyboards.clinics import (
    KEEP_NAME_TEXT,
    KEEP_PRICE_TEXT,
    cancel_keyboard,
    clinics_menu_keyboard,
    edit_clinic_confirmation_keyboard,
    edit_name_keyboard,
    edit_price_keyboard,
)
from keyboards.main import get_main_keyboard
from states.clinic import AddClinic, EditClinic


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


def validate_clinic_name(text: str) -> str | None:
    clinic_name = text.strip()

    if len(clinic_name) < 2:
        return None

    if len(clinic_name) > 60:
        return None

    return clinic_name


@router.message(F.text == "😼 Поликлиники и цены")
async def show_clinics_handler(message: Message) -> None:
    clinics = await get_clinics()

    if not clinics:
        await message.answer(
            "Поликлиники пока не добавлены.\n\n"
            "Нажмите кнопку ниже, чтобы добавить первую.",
            reply_markup=clinics_menu_keyboard(clinics),
        )
        return

    lines = ["🏥 <b>Поликлиники и цены</b>\n"]

    for _, name, primary_price, secondary_price in clinics:
        lines.append(
            f"<b>{escape(name)}</b>\n"
            f"Первичный: {format_price(primary_price)} ₽\n"
            f"Вторичный: {format_price(secondary_price)} ₽"
        )

    await message.answer(
        "\n\n".join(lines),
        reply_markup=clinics_menu_keyboard(clinics),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "clinic:add")
async def start_add_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(AddClinic.name)

    if callback.message:
        await callback.message.answer(
            "Введите название поликлиники.\n\n"
            "Например: Поликлиника №5",
            reply_markup=cancel_keyboard,
        )

    await callback.answer()


@router.callback_query(F.data.regexp(r"^clinic:edit:\d+$"))
async def start_edit_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
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

    await state.clear()
    await state.update_data(
        clinic_id=clinic_id,
        old_name=name,
        old_primary_price=primary_price,
        old_secondary_price=secondary_price,
    )
    await state.set_state(EditClinic.name)

    if callback.message:
        await callback.message.answer(
            "✏️ <b>Изменение поликлиники</b>\n\n"
            f"Текущее название: <b>{escape(name)}</b>\n\n"
            "Введите новое название или оставьте текущее.",
            reply_markup=edit_name_keyboard,
            parse_mode="HTML",
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


@router.message(AddClinic.name)
async def clinic_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите название текстом.")
        return

    clinic_name = validate_clinic_name(message.text)

    if clinic_name is None:
        await message.answer(
            "Название должно содержать от 2 до 60 символов.\n"
            "Введите название ещё раз."
        )
        return

    await state.update_data(name=clinic_name)
    await state.set_state(AddClinic.primary_price)

    await message.answer(
        "Введите стоимость первичного приёма в рублях.\n\n"
        "Например: 2500"
    )


@router.message(AddClinic.primary_price)
async def primary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите сумму цифрами.")
        return

    primary_price = parse_price(message.text)

    if primary_price is None:
        await message.answer(
            "Не удалось распознать сумму.\n\n"
            "Введите целое число, например: 2500"
        )
        return

    await state.update_data(primary_price=primary_price)
    await state.set_state(AddClinic.secondary_price)

    await message.answer(
        "Введите стоимость вторичного приёма в рублях.\n\n"
        "Например: 1800"
    )


@router.message(AddClinic.secondary_price)
async def secondary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите сумму цифрами.")
        return

    secondary_price = parse_price(message.text)

    if secondary_price is None:
        await message.answer(
            "Не удалось распознать сумму.\n\n"
            "Введите целое число, например: 1800"
        )
        return

    data = await state.get_data()

    clinic_name = str(data["name"])
    primary_price = int(data["primary_price"])

    created = await add_clinic(
        name=clinic_name,
        primary_price=primary_price,
        secondary_price=secondary_price,
    )

    await state.clear()

    if not created:
        await message.answer(
            "Поликлиника с таким названием уже существует.",
            reply_markup=get_main_keyboard(is_admin=True),
        )
        return

    await message.answer(
        "✅ Поликлиника добавлена.\n\n"
        f"🏥 {clinic_name}\n"
        f"Первичный: {format_price(primary_price)} ₽\n"
        f"Вторичный: {format_price(secondary_price)} ₽",
        reply_markup=get_main_keyboard(is_admin=True),
    )


@router.message(EditClinic.name)
async def edit_clinic_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите название текстом.")
        return

    data = await state.get_data()
    old_name = str(data["old_name"])

    if message.text == KEEP_NAME_TEXT:
        new_name = old_name
    else:
        parsed_name = validate_clinic_name(message.text)

        if parsed_name is None:
            await message.answer(
                "Название должно содержать от 2 до 60 символов.\n"
                "Введите название ещё раз."
            )
            return

        new_name = parsed_name

    await state.update_data(new_name=new_name)
    await state.set_state(EditClinic.primary_price)

    old_primary_price = int(data["old_primary_price"])

    await message.answer(
        "Введите новую стоимость первичного приёма.\n\n"
        f"Сейчас: {format_price(old_primary_price)} ₽",
        reply_markup=edit_price_keyboard,
    )


@router.message(EditClinic.primary_price)
async def edit_primary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите сумму цифрами.")
        return

    data = await state.get_data()
    old_primary_price = int(data["old_primary_price"])

    if message.text == KEEP_PRICE_TEXT:
        primary_price = old_primary_price
    else:
        parsed_price = parse_price(message.text)

        if parsed_price is None:
            await message.answer(
                "Не удалось распознать сумму.\n\n"
                "Введите целое число, например: 2500"
            )
            return

        primary_price = parsed_price

    await state.update_data(new_primary_price=primary_price)
    await state.set_state(EditClinic.secondary_price)

    old_secondary_price = int(data["old_secondary_price"])

    await message.answer(
        "Введите новую стоимость вторичного приёма.\n\n"
        f"Сейчас: {format_price(old_secondary_price)} ₽",
        reply_markup=edit_price_keyboard,
    )


@router.message(EditClinic.secondary_price)
async def edit_secondary_price_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer("Введите сумму цифрами.")
        return

    data = await state.get_data()
    old_secondary_price = int(data["old_secondary_price"])

    if message.text == KEEP_PRICE_TEXT:
        secondary_price = old_secondary_price
    else:
        parsed_price = parse_price(message.text)

        if parsed_price is None:
            await message.answer(
                "Не удалось распознать сумму.\n\n"
                "Введите целое число, например: 1800"
            )
            return

        secondary_price = parsed_price

    await state.update_data(new_secondary_price=secondary_price)
    await state.set_state(EditClinic.confirmation)

    data = await state.get_data()

    old_name = escape(str(data["old_name"]))
    new_name = escape(str(data["new_name"]))
    old_primary_price = int(data["old_primary_price"])
    new_primary_price = int(data["new_primary_price"])

    await message.answer(
        "Проверьте изменения:\n\n"
        "<b>Было</b>\n"
        f"🏥 {old_name}\n"
        f"Первичный: {format_price(old_primary_price)} ₽\n"
        f"Вторичный: {format_price(old_secondary_price)} ₽\n\n"
        "<b>Станет</b>\n"
        f"🏥 {new_name}\n"
        f"Первичный: {format_price(new_primary_price)} ₽\n"
        f"Вторичный: {format_price(secondary_price)} ₽\n\n"
        "Сохранить изменения?",
        reply_markup=edit_clinic_confirmation_keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    EditClinic.confirmation,
    F.data == "clinic:edit:save",
)
async def save_edited_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    clinic_id = int(data["clinic_id"])
    clinic_name = str(data["new_name"])
    primary_price = int(data["new_primary_price"])
    secondary_price = int(data["new_secondary_price"])

    result = await update_clinic(
        clinic_id=clinic_id,
        name=clinic_name,
        primary_price=primary_price,
        secondary_price=secondary_price,
    )

    await state.clear()

    if result == "not_found":
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    if result == "duplicate_name":
        if callback.message:
            await callback.message.edit_text(
                "Поликлиника с таким названием уже существует."
            )
            await callback.message.answer(
                "Выберите действие:",
                reply_markup=get_main_keyboard(is_admin=True),
            )

        await callback.answer(
            "Название уже занято.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Поликлиника обновлена</b>\n\n"
            f"🏥 {escape(clinic_name)}\n"
            f"Первичный: {format_price(primary_price)} ₽\n"
            f"Вторичный: {format_price(secondary_price)} ₽",
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer("Изменения сохранены")


@router.callback_query(
    EditClinic.confirmation,
    F.data == "clinic:edit:cancel",
)
async def cancel_edited_clinic_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Изменение поликлиники отменено."
        )
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer()