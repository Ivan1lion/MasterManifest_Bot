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
