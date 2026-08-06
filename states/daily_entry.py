from aiogram.fsm.state import State, StatesGroup


class DailyEntry(StatesGroup):
    primary_count = State()
    secondary_count = State()
    confirmation = State()
