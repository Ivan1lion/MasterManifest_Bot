import os
import re
import base64
from uuid import uuid4
import aiohttp

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

for_user_router = Router()

# ==== FSM для запроса email ====
class EmailState(StatesGroup):
    waiting_for_email = State()

# ==== Кнопки выбора способа получения чека ====
def receipt_choice_keyboard(amount_key: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 Отправить на телефон", callback_data=f"receipt_phone:{amount_key}")
    kb.button(text="📧 На email", callback_data=f"receipt_email:{amount_key}")
    return kb.as_markup()

# ==== Обработка выбора тарифа ====
@for_user_router.callback_query(F.data.startswith("pay"))
async def choose_receipt_method(callback: CallbackQuery):
    data_key = callback.data  # например "pay30"
    await callback.message.answer(
        "Куда отправить чек?",
        reply_markup=receipt_choice_keyboard(data_key)
    )
    await callback.answer()

# ==== 1. Чек на телефон ====
@for_user_router.callback_query(F.data.startswith("receipt_phone"))
async def request_phone(callback: CallbackQuery):
    amount_key = callback.data.split(":")[1]

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой телефон", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(
        "Пожалуйста, отправьте свой номер телефона:",
        reply_markup=kb
    )
    await callback.answer()

    # Сохраняем выбранный тариф в state
    state: FSMContext = callback.bot['fsm_context']
    await state.set_data({"amount_key": amount_key, "method": "phone"})

# ==== Получение контакта и создание платежа ====
@for_user_router.message(F.contact)
async def got_contact(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    user_data = await state.get_data()
    amount_key = user_data.get("amount_key")
    phone_number = message.contact.phone_number

    await create_yookassa_payment(message, bot, amount_key, phone=phone_number)
    await state.clear()

# ==== 2. Чек на email ====
@for_user_router.callback_query(F.data.startswith("receipt_email"))
async def request_email(callback: CallbackQuery, state: FSMContext):
    amount_key = callback.data.split(":")[1]
    await state.set_data({"amount_key": amount_key, "method": "email"})
    await callback.message.answer("Пришлите email в чат. На него будет выслан чек:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EmailState.waiting_for_email)
    await callback.answer()

# ==== Получение email и создание платежа ====
@for_user_router.message(EmailState.waiting_for_email)
async def got_email(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    email = message.text.strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await message.answer("❌ Пожалуйста, введите корректный email.")
        return

    user_data = await state.get_data()
    amount_key = user_data.get("amount_key")

    await create_yookassa_payment(message, bot, amount_key, email=email)
    await state.clear()

# ==== Создание платежа с чеком ====
async def create_yookassa_payment(message: Message, bot: Bot, amount_key: str, phone=None, email=None):
    amount_map = {
        "pay30": 30,
        "pay550": 550,
        "pay2500": 2500
    }
    amount = amount_map.get(amount_key)
    if not amount:
        await message.answer("Неизвестная сумма.")
        return

    return_url = f"https://t.me/{(await bot.me()).username}"

    receipt = {
        "customer": {},
        "items": [
            {
                "description": f"Покупка на {amount}₽",
                "quantity": "1.00",
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "vat_code": 1
            }
        ]
    }
    if phone:
        receipt["customer"]["phone"] = phone
    if email:
        receipt["customer"]["email"] = email

    payment_payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": f"Покупка на {amount}₽",
        "metadata": {"telegram_id": str(message.from_user.id)},
        "receipt": receipt
    }

    def base64_auth():
        shop_id = os.getenv("YOOKASSA_SHOP_ID")
        secret = os.getenv("YOOKASSA_SECRET_KEY")
        raw = f"{shop_id}:{secret}".encode()
        return base64.b64encode(raw).decode()

    headers = {
        "Authorization": f"Basic {base64_auth()}",
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid4())
    }

    try:
        async with aiohttp.ClientSession() as session_http:
            async with session_http.post(
                url="https://api.yookassa.ru/v3/payments",
                json=payment_payload,
                headers=headers
            ) as resp:
                payment_response = await resp.json()

        print("📦 Ответ от ЮKassa:", payment_response)

        if "confirmation" not in payment_response:
            error_text = payment_response.get("description", "Нет поля confirmation")
            await message.answer(f"❌ Ошибка ЮKassa: {error_text}")
            return

        confirmation_url = payment_response["confirmation"]["confirmation_url"]
        await message.answer(
            f'Вы приобретаете дополнительные запросы'
            f'\n\nПосле успешной оплаты, они отобразятся в разделе -> ⭐️ Баланс'
            f'\n\n<blockquote>Оплата производится через Yoomoney (сервис электронных платежей ПАО "Сбербанк")</blockquote>',
            reply_markup=InlineKeyboardBuilder().button(text="💳 Перейти к оплате", url=confirmation_url).as_markup()
        )

    except Exception as e:
        print("❌ Ошибка при создании платежа:", e)
        await message.answer("Ошибка при попытке создать платёж. Подробности в логах.")
