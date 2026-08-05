from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_keyboard(is_admin: bool = True) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🐾 Добавить приём"),
            ],
            [
                KeyboardButton(text="📅 Добавить за дату"),
            ],
            [
                KeyboardButton(text="😺 Сегодня"),
                KeyboardButton(text="😸 Этот месяц"),
            ],
            [
                KeyboardButton(text="🐈‍⬛ Выбрать период"),
            ],
            [
                KeyboardButton(text="🙀 Последний приём"),
                KeyboardButton(text="😼 Поликлиники и цены"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


main_keyboard = get_main_keyboard(True)