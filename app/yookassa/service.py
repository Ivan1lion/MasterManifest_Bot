from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User

PRICE_TO_QUERIES = {
    30: 1,
    349: 20,
    1700: 100,
}

async def process_payment(session: AsyncSession, telegram_id: int, amount: int) -> bool:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    extra_requests = PRICE_TO_QUERIES.get(amount)
    if not extra_requests:
        return False

    user.requests_left += extra_requests
    await session.commit()
    return True
