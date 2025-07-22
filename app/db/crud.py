from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User
import uuid


# Получить пользователя или создать нового
async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        return user

    # Новый пользователь → создать с уникальным thread_id
    new_user = User(
        telegram_id=telegram_id,
        thread_id=str(uuid.uuid4()),
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
