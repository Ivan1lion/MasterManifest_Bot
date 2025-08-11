from aiogram.fsm.state import State, StatesGroup

class PaymentState(StatesGroup):
    awaiting_contact = State()
    awaiting_email = State()
