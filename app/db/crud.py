from aiogram import Bot
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from .models import User
import os

# Инициализируем OpenAI клиента один раз
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Получить пользователя или создать нового
async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    # Проверка: есть ли пользователь
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        return user

    # Новый пользователь → создать thread через OpenAI
    thread = await client.beta.threads.create()
    if not thread or not thread.id:
        raise RuntimeError("❌ Не удалось создать thread через OpenAI API")

    new_user = User(
        telegram_id=telegram_id,
        thread_id=thread.id,  # 👈 это будет вида thread_abc123...
        requests_left=2,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


# Уменьшить количество оставшихся запросов
async def decrement_requests(session: AsyncSession, telegram_id: int) -> None:
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(requests_left=User.requests_left - 1)
    )
    await session.commit()


# на случай перезагрузки/сбоя бота
async def notify_pending_users(bot: Bot, session_factory):
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.request_status == 'pending'))
        users = result.scalars().all()
        for user in users:
            try:
                await bot.send_message(user.telegram_id, f"⚠️ Извините, сбой на сервере"
                                                         f"\n\nПредыдущий запрос не был "
                                                         "обработан. Повторите его пожалуйста")
                user.status = 'error'
            except Exception as e:
                print(f"Ошибка при уведомлении пользователя {user.telegram_id}: {e}")
        await session.commit()
