from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message


router = Router()


@router.message(Command("myid"))
async def show_user_id_handler(message: Message) -> None:
    if message.from_user is None:
        await message.answer(
            "Не удалось определить Telegram ID."
        )
        return

    await message.answer(
        "🆔 <b>Ваш Telegram ID</b>\n\n"
        f"<code>{message.from_user.id}</code>\n\n"
        "Скопируйте только цифры.",
        parse_mode="HTML",
    )
