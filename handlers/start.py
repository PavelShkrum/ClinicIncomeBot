from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.main import get_main_keyboard


router = Router()


@router.message(CommandStart())
async def start_handler(
    message: Message,
    is_admin: bool,
) -> None:
    role_name = "администратор" if is_admin else "пользователь"

    await message.answer(
        "Бот учёта приёмов запущен.\n\n"
        f"Ваша роль: {role_name}.\n\n"
        "Добавляйте первичные и вторичные приёмы "
        "и следите за заработанной суммой.",
        reply_markup=get_main_keyboard(is_admin),
    )
