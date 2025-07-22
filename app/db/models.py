from sqlalchemy import Column, BigInteger, Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime
import pytz

Base = declarative_base()
moscow_tz = pytz.timezone("Europe/Moscow")

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram user_id
    thread_id = Column(String, nullable=True)  # OpenAI thread_id (один на пользователя)
    request_count = Column(Integer, default=2)  # Кол-во оставшихся запросов
    is_subscribed = Column(Boolean, default=False)  # флаг подписки
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(moscow_tz))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(moscow_tz))
