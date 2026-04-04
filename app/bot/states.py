from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_phone = State()


class CardStates(StatesGroup):
    waiting_for_card_number = State()
    waiting_for_holder_name = State()


class WithdrawalStates(StatesGroup):
    waiting_for_amount = State()
