"""
Middleware автоматически:
1. Создаёт / берёт пользователя из БД.
2. Кладёт `user` и `session` в data, чтобы их
   можно было просто указать как параметры в хэндлере.
3. После хэндлера делает commit и закрывает сессию.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import SessionLocal
from app.db.crud import get_user, create_user
from app.db.models import User


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = getattr(event, "from_user", None)
        if tg_user is None:                             # если апдейт без from_user
            return await handler(event, data)

        async with SessionLocal() as session:           # один session на апдейт
            user: User | None = await get_user(session, tg_user.id)
            if user is None:
                user = await create_user(session, tg_user.id)

            data["session"] = session                   # доступен как параметр в хэндлере
            data["user"] = user

            result = await handler(event, data)         # запускаем хэндлер
            await session.commit()                      # фиксируем возможные изменения
            return result
