import asyncio
import os
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, CallbackQuery, InputMediaPhoto, PreCheckoutQuery, ContentType, SuccessfulPayment
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# from yookassa import Payment
# import uuid


from app.handlers.text_for_user import text_privacy, text_offer, text_hello, text_info, text_hello2
import app.handlers.keyboards as kb
from app.db.crud import get_or_create_user, get_last_post_id, set_last_post_id
from app.db.models import User
from app.db.config import session_maker
from app.openai_assistant.client import ask_assistant
from app.openai_assistant.queue import openai_queue


channel = int(os.getenv("CHANNEL_ID"))


router = Router()
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
    await get_or_create_user(session, message.from_user.id)
    string = (f"📖 Что такое @MasterManifest_Bot и как он поможет вам?"
              f"\n\nПредставьте, что у вас есть доступ к мудрому собеседнику, который:"
              f"\n\n✨ Читал тысячи книг, статей и исследований"
              f"\n✨ Понимает, как устроено мышление и как работают ваши убеждения"
              f"\n✨ Может помочь вам изменить мышление, поверить в себя и научиться использовать силу манифестации"
              f"\n\nЭто и есть @MasterManifest_Bot — умный виртуальный помощник, созданный с помощью технологий "
              f"искусственного интеллекта. Он умеет понимать ваши вопросы и давать ответы простым, понятным языком — без осуждения "
              f"и лишней теории\n"
              f"\nНо самое главное — этот бот обучен специально, чтобы помогать людям в таких темах, как:\n"
              f"\n💭 Материализация желаний"
              f"\n🧘‍♀️ Сила мысли и трансформация мышления"
              f"\n💎 Философия богатства"
              f"\n🌌 Закон притяжения"
              f"\n🌱 Работа с подсознанием и внутренними установками\n"
              f"\nПросто напишите свой вопрос — и получите ответ, вдохновение или пошаговый совет, как изменить свою "
              f"реальность через мысли и чувства"
              f"\n\n<i>Нажмите на команду</i> /info <i>что бы узнать как правильно вести диалог с ботом</i>")
    await message.answer(text=string)
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if user.requests_left == 0:
        await message.answer(f"🚫 У вас закончились запросы\n\nПожалуйста, пополните баланс", reply_markup=kb.pay)
        return





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
        typing_msg = await message.answer("[🙋‍♀️Mari]: Master Manifest пишет 💬") # Отправляем текст

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

# Пример колбэков
@router.callback_query(F.data.startswith("pay"))
async def handle_payment(callback: types.CallbackQuery):
    PRICE_MAP = {
        "pay30": 30,
        "pay349": 349,
        "pay1700": 1700,
    }

    price_code = callback.data
    amount = PRICE_MAP.get(price_code)
    if not amount:
        await callback.answer("Неверная сумма", show_alert=True)
        return

    payment = Payment.create({
        "amount": {
            "value": f"{amount}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/your_bot_name"
        },
        "capture": True,
        "description": f"Покупка {amount}₽",
        "metadata": {
            "telegram_id": callback.from_user.id
        }
    }, uuid.uuid4())

    confirmation_url = payment.confirmation.confirmation_url
    await callback.message.answer(f"Перейдите по ссылке для оплаты:\n{confirmation_url}")
    await callback.answer()



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
                    message_id=message.message_id
                )
            except Exception as e:
                print(f"❌ Ошибка отправки пользователю {user_id}: {e}")

        # Обновляем last_post_id
        await set_last_post_id(session, message.message_id)




