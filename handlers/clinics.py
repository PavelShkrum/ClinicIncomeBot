from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.db import (
    add_clinic,
    get_clinic_by_id,
    get_clinics,
    update_clinic_prices,
)
from keyboards.clinics import (
    cancel_keyboard,
    clinics_menu_keyboard,
    edit_prices_confirmation_keyboard,
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
        clinic_name=name,
        old_primary_price=primary_price,
        old_secondary_price=secondary_price,
    )
    await state.set_state(EditClinic.primary_price)

    if callback.message:
        await callback.message.answer(
            f"✏️ Изменение цен: <b>{escape(name)}</b>\n\n"
            "Введите новую стоимость первичного приёма.\n"
            f"Сейчас: {format_price(primary_price)} ₽",
            reply_markup=cancel_keyboard,
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

    clinic_name = message.text.strip()

    if len(clinic_name) < 2:
        await message.answer(
            "Название слишком короткое. Введите ещё раз."
        )
        return

    if len(clinic_name) > 60:
        await message.answer(
            "Название слишком длинное. Используйте не более 60 символов."
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


@router.message(EditClinic.primary_price)
async def edit_primary_price_handler(
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

    await state.update_data(new_primary_price=primary_price)
    await state.set_state(EditClinic.secondary_price)

    data = await state.get_data()
    old_secondary_price = int(data["old_secondary_price"])

    await message.answer(
        "Введите новую стоимость вторичного приёма.\n"
        f"Сейчас: {format_price(old_secondary_price)} ₽"
    )


@router.message(EditClinic.secondary_price)
async def edit_secondary_price_handler(
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

    await state.update_data(new_secondary_price=secondary_price)
    await state.set_state(EditClinic.confirmation)

    data = await state.get_data()

    clinic_name = escape(str(data["clinic_name"]))
    primary_price = int(data["new_primary_price"])

    await message.answer(
        "Проверьте новые цены:\n\n"
        f"🏥 <b>{clinic_name}</b>\n"
        f"Первичный: {format_price(primary_price)} ₽\n"
        f"Вторичный: {format_price(secondary_price)} ₽\n\n"
        "Сохранить изменения?",
        reply_markup=edit_prices_confirmation_keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    EditClinic.confirmation,
    F.data == "clinic:edit:save",
)
async def save_edited_prices_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    clinic_id = int(data["clinic_id"])
    clinic_name = str(data["clinic_name"])
    primary_price = int(data["new_primary_price"])
    secondary_price = int(data["new_secondary_price"])

    updated = await update_clinic_prices(
        clinic_id=clinic_id,
        primary_price=primary_price,
        secondary_price=secondary_price,
    )

    await state.clear()

    if not updated:
        await callback.answer(
            "Поликлиника не найдена.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "✅ <b>Цены обновлены</b>\n\n"
            f"🏥 {escape(clinic_name)}\n"
            f"Первичный: {format_price(primary_price)} ₽\n"
            f"Вторичный: {format_price(secondary_price)} ₽",
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer("Новые цены сохранены")


@router.callback_query(
    EditClinic.confirmation,
    F.data == "clinic:edit:cancel",
)
async def cancel_edited_prices_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Изменение цен отменено."
        )
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard(is_admin=True),
        )

    await callback.answer()
