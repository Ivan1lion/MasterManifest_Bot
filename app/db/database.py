from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.config import config

engine = create_async_engine(config.db_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
