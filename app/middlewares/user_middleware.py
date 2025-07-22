from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud import get_or_create_user
from app.database.config import async_session


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session() as session:
            user = await get_or_create_user(session, event.from_user.id)
            data["user"] = user
        return await handler(event, data)
