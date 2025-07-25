from aiogram import Router
from aiogram.types import Update
from fastapi import Request
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from app.yookassa.schemas import YooKassaWebhook
from app.yookassa.service import process_payment
from yookassa.domain.notification import WebhookNotificationEventType
from yookassa.domain.notification import WebhookNotificationFactory
from yookassa.domain.common import SecurityHelper
from aiogram.types import JSONable
from app.middlewares.db_session import get_session

import logging

router = Router()
logger = logging.getLogger(__name__)

@router.post("/yookassa/webhook")
async def yookassa_webhook(request: Request):
    data = await request.json()
    logger.info(f"YooKassa Webhook received: {data}")

    notification = WebhookNotificationFactory().create(data)

    if notification.event != WebhookNotificationEventType.PAYMENT_SUCCEEDED:
        return {"status": "ignored"}

    payment = notification.object
    metadata = payment.metadata
    amount = int(float(payment.amount.value))  # float → int
    telegram_id = int(metadata.get("telegram_id"))

    async with get_session() as session:
        updated = await process_payment(session, telegram_id, amount)
        if updated:
            return {"status": "ok"}
        else:
            return {"status": "user_not_found"}
