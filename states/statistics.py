from aiogram.fsm.state import State, StatesGroup


class PeriodSelection(StatesGroup):
    choosing_start = State()
    choosing_end = State()
