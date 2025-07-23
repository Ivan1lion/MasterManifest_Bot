from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, CallbackQuery, InputMediaPhoto, PreCheckoutQuery, ContentType, SuccessfulPayment
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.handlers.text_for_user import text_privacy, text_offer
import app.handlers.keyboards as kb
from app.db.crud import get_or_create_user
from app.db.models import User
from app.openai_assistant.client import ask_assistant
from app.openai_assistant.queue import openai_queue


for_user_router = Router()




# команды для кнопки МЕНЮ

@for_user_router.message(Command("balance"))
async def policy_cmd(message: Message, bot: Bot, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if user.requests_left == 0:
        await message.answer("🚫 У вас закончились запросы\n\nПожалуйста, пополните баланс", reply_markup=kb.pay)
        return
    text_balance = (f"Количество оставшихся запросов: {user.requests_left}"
                    f"\n\nПополнить баланс можно через кнопки ниже")
    await message.answer(text_balance, reply_markup=kb.pay)


@for_user_router.message(Command("privacy"))
async def policy_cmd(message: Message):
    await message.answer(text_privacy)


@for_user_router.message(Command("offer"))
async def offer_cmd(message: Message):
    await message.answer(text_offer)


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
              f"реальность через мысли и чувства")
    await message.answer(text=string)
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if user.requests_left == 0:
        await message.answer("🚫 У вас закончились запросы\n\nПожалуйста, пополните баланс", reply_markup=kb.pay)
        return





# ОБРАБОТЧИКИ

@for_user_router.message(~(F.text))
async def filter(message: Message):
        await message.delete()
        await message.answer("Запросы только в формате текста")




@for_user_router.message(F.text)
async def handle_text(message: Message, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if user.requests_left == 0:
        await message.answer("❌ У вас закончились запросы.")
        return

    if not openai_queue:
        await message.answer("Ассистент временно недоступен.")
        return

    try:
        answer = await ask_assistant(
            queue=openai_queue,
            user_id=user.telegram_id,
            thread_id=user.thread_id,
            message=message.text
        )
        await message.answer(answer)
        user.requests_left -= 1
        await session.commit()
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обработке запроса: {str(e)}")

