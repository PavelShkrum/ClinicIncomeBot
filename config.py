import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    admin_id: int
    user_id: int


def get_required_telegram_id(variable_name: str) -> int:
    value = os.getenv(variable_name)

    if not value or not value.isdigit():
        raise RuntimeError(
            f"В файле .env не указан корректный {variable_name}."
        )

    return int(value)


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")

    if not bot_token:
        raise RuntimeError(
            "Не найден BOT_TOKEN. Проверь файл "
            "C:\\Bots\\ClinicIncomeBot\\.env"
        )

    admin_id = get_required_telegram_id("ADMIN_ID")
    user_id = get_required_telegram_id("USER_ID")

    if admin_id == user_id:
        raise RuntimeError(
            "ADMIN_ID и USER_ID должны принадлежать разным аккаунтам."
        )

    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        user_id=user_id,
    )
