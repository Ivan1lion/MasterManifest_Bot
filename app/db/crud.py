from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User

async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, user_id: int) -> User:
    user = User(id=user_id)
    session.add(user)
    await session.commit()
    return user

async def decrement_request_count(session: AsyncSession, user_id: int):
    user = await get_user(session, user_id)
    if user and user.request_count > 0:
        user.request_count -= 1
        await session.commit()

async def increment_request_count(session: AsyncSession, user_id: int, amount: int):
    user = await get_user(session, user_id)
    if user:
        user.request_count += amount
        await session.commit()

async def update_thread_id(session: AsyncSession, user_id: int, thread_id: str):
    user = await get_user(session, user_id)
    if user:
        user.thread_id = thread_id
        await session.commit()
