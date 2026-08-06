from aiogram.fsm.state import State, StatesGroup


class AddSpecialty(StatesGroup):
    name = State()
    primary_price = State()
    secondary_price = State()
    confirmation = State()


class EditSpecialty(StatesGroup):
    name = State()
    primary_price = State()
    secondary_price = State()
    confirmation = State()
