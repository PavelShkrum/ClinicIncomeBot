from aiogram.fsm.state import State, StatesGroup


class AddClinic(StatesGroup):
    name = State()
    specialty_name = State()
    primary_price = State()
    secondary_price = State()
    confirmation = State()


class RenameClinic(StatesGroup):
    name = State()
    confirmation = State()
