# db_session.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Awaitable, Dict, Any
from app.db.models import User


class DataBaseSession(BaseMiddleware):
    def __init__(self, session_pool):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with self.session_pool() as session:
            data["session"] = session

            # 🚀 Получаем Telegram ID
            tg_id = data["event_from_user"].id

            # 🚀 Пробуем найти юзера
            result = await session.execute(select(User).where(User.telegram_id == tg_id))
            user = result.scalar_one_or_none()

            # ✅ Если нет — создаем
            if user is None:
                user = User(telegram_id=tg_id)
                session.add(user)
                await session.commit()
                await session.refresh(user)

            data["user"] = user  # Добавим в data
            return await handler(event, data)
