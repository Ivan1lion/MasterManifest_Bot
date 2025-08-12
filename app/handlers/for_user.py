import asyncio
import os
import random
import string
from uuid import uuid4
import aiohttp
import base64
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, CallbackQuery, InputMediaPhoto, PreCheckoutQuery, ContentType, SuccessfulPayment
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from app.handlers.text_for_user import text_privacy, text_offer, text_hello, text_info, text_hello2
import app.handlers.keyboards as kb
from app.handlers.keyboards import payment_button_keyboard
from app.db.crud import get_or_create_user, get_last_post_id, set_last_post_id
from app.db.models import User
from app.db.config import session_maker
from app.openai_assistant.client import ask_assistant
from app.openai_assistant.queue import openai_queue


channel = int(os.getenv("CHANNEL_ID"))

for_user_router = Router()


# команды для кнопки МЕНЮ
@for_user_router.message(Command("info"))
async def policy_cmd(message: Message):
    await message.answer(text_info)


@for_user_router.message(Command("balance"))
async def policy_cmd(message: Message, bot: Bot, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if user.requests_left == 0:
        await message.answer(f"🚫 У вас закончились запросы"
                             f"\n\nПожалуйста, пополните баланс", reply_markup=kb.pay)
        return
    text_balance = (f"Количество запросов\n"
                    f"на вашем балансе: [ {user.requests_left} ]"
                    f"\n\nПополнить баланс можно через кнопки ниже")
    await message.answer(text_balance, reply_markup=kb.pay)


@for_user_router.message(Command("hello"))
async def offer_cmd(message: Message):
    # Получаем абсолютный путь к медиа-файлу
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    GIF_PATH = os.path.join(BASE_DIR, "..", "mediafile_for_bot", "My_photo.png")
    gif_file = FSInputFile(os.path.abspath(GIF_PATH))
    # Отправляем медиа
    wait_msg = await message.answer_photo(photo=gif_file, caption=text_hello)
    await message.answer(text_hello2)


@for_user_router.message(Command("privacy"))
async def policy_cmd(message: Message):
    await message.answer(text_privacy)


@for_user_router.message(Command("offer"))
async def offer_cmd(message: Message):
    await message.answer(text_offer)







# команд СТАРТ
@for_user_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, session: AsyncSession):
    await get_or_create_user(session, message.from_user.id, message.from_user.username)
    typing_msg = await message.answer("Master Manifest пишет 💬")  # Отправляем текст
    await bot.send_chat_action(chat_id=message.chat.id, action="typing") # Показываем "печатает"
    await asyncio.sleep(4)
    await typing_msg.delete()
    string = (f"Я — Master Manifest. Объясняю сложное простым языком"
              f"\n\n<blockquote>Моя задача — помочь тебе разобраться с тем как превратить желания в реальность, раскрыть силу мысли и убрать "
              f"внутренние блоки, мешающие изобилию "
              f"\n\nВообрази, что ты уже живёшь той жизнью, о которой мечтаешь — я (будучи огромной библиотекой знаний) "
              f"подскажу, как к ней прийти быстрее</blockquote> "
              f"\n\n📖 Вот как мы можем работать:"
              f"\n1️⃣ Ты задаёшь вопрос или описываешь ситуацию"
              f"\n2️⃣ Я даю понятные и практичные рекомендации"
              f"\n\nНо для начала представься пожалуйста. Это важно, чтобы я понимал с кем я разговариваю "
              f"(мужчина или женщина) и как мне к тебе обращаться "
              f"\n\nФормат:"
              f"\n<blockquote>Меня зовут <i>(твоё имя)</i></blockquote>"
              f"\n\nИтак, как тебя зовут? 👋")
    await message.answer(text=string)






# ОБРАБОТЧИКИ

@for_user_router.message(~(F.text))
async def filter(message: Message):
    await message.delete()
    await message.answer("Запросы только в формате текста")





# обработка запросов пользователя


# Функция, чтобы крутился индикатор "печатает"
async def send_typing(bot, chat_id, stop_event):
    while not stop_event.is_set():
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(4.5)

@for_user_router.message(F.text)
async def handle_text(message: Message, session: AsyncSession, bot: Bot):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if user.requests_left == 0:
        await message.answer(f"🚫 У вас закончились запросы\n\nПожалуйста, пополните баланс"
                             f"\n\n<a href='https://telegra.ph/pvapavp-07-04'>"
                             "(Почему бот стал платным?)</a>", reply_markup=kb.pay)
        return

    if not openai_queue:
        await message.answer("⚠️ Ассистент временно недоступен\n\nПовторите пожалуйста запрос позже")
        return

    try:
        typing_msg = await message.answer("Master Manifest пишет 💬") # Отправляем текст

        # 🟡 Обновляем статус запроса
        user.request_status = "pending"
        await session.commit()

        # Стартуем фоновый "набор текста"
        stop_event = asyncio.Event()
        typing_task = asyncio.create_task(send_typing(bot, message.chat.id, stop_event))

        answer = await ask_assistant(
            queue=openai_queue,
            user_id=user.telegram_id,
            thread_id=user.thread_id,
            message=message.text
        )

        # Убираем индикаторы
        stop_event.set()
        typing_task.cancel()
        await typing_msg.delete()


        await message.answer(answer, parse_mode=ParseMode.MARKDOWN)

        # ✅ Запрос выполнен
        user.requests_left -= 1
        user.request_status = "complete"
        await session.commit()
    except Exception as e:
        await message.answer(f'⚠️ Ошибка при обработке запроса: {str(e)}\n\nЕсли эта ошибка повторится сообщите '
                             f'пожалуйста об этом администратору нашего сервиса '
                             f'<a href="https://t.me/RomanMo_admin">@RomanMo_admin</a>')




# Приём платежа


def generate_random_email():   # Генерируем случайную строку длиной 10 символов
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{random_str}@yandex.ru"

@for_user_router.callback_query(F.data.startswith("pay"))
async def process_payment(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    telegram_id = callback.from_user.id
    amount_map = {
        "pay30": 30,
        "pay550": 550,
        "pay2500": 2500
    }

    data_key = callback.data
    amount = amount_map.get(data_key)
    if not amount:
        await callback.answer("Неизвестная сумма", show_alert=True)
        return

    return_url = f"https://t.me/{(await bot.me()).username}"


    # Получаем пользователя
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    # Генерируем email, если он ещё не задан
    if not user.email or user.email == "idle":
        user.email = generate_random_email()
        await session.commit()

    payment_payload = {
        "amount": {
            "value": f"{amount:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": f"Покупка на {amount}₽",
        "metadata": {
            "telegram_id": str(telegram_id)
        },
        "receipt": {
            "customer": {
                "email": user.email
            },
            "items": [
                {
                    "description": f"Покупка на {amount}₽",
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": "RUB"
                    },
                    "vat_code": 1
                }
            ]
        }
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
            await callback.message.answer(f"❌ Ошибка ЮKassa: {error_text}")
            return

        confirmation_url = payment_response["confirmation"]["confirmation_url"]
        await callback.message.answer(
            f'Вы приобретаете дополнительные запросы'
            f'\n\nПосле успешной оплаты, они отобразятся в разделе -> ⭐️ Баланс'
            f'\n\n<blockquote>Оплата производится через Yoomoney (cервис электронных платежей ПАО "Сбербанк")</blockquote>',
            reply_markup=payment_button_keyboard(confirmation_url)
        )
        await callback.answer()

    except Exception as e:
        print("❌ Ошибка при создании платежа:", e)
        await callback.message.answer("Ошибка при попытке создать платёж. Подробности в логах.")



# Отправка сообщений из канала Mari

@for_user_router.channel_post()
async def forward_post_to_users(message: Message, bot: Bot):
    if message.chat.id != channel:
        return

    async with session_maker() as session:
        last_id = await get_last_post_id(session)
        if message.message_id <= last_id:
            return  # уже отправляли пост

        # Получаем всех пользователей
        result = await session.execute(select(User.telegram_id))
        users = result.scalars().all()

        for user_id in users:
            try:
                await bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=channel,
                    message_id=message.message_id,
                )
            except Exception as e:
                print(f"❌ Ошибка отправки пользователю {user_id}: {e}")

        # Обновляем last_post_id
        await set_last_post_id(session, message.message_id)





