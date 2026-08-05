from aiogram.fsm.state import State, StatesGroup


class AddClinic(StatesGroup):
    name = State()
    primary_price = State()
    secondary_price = State()


class EditClinic(StatesGroup):
    name = State()
    primary_price = State()
    secondary_price = State()
    confirmation = State()