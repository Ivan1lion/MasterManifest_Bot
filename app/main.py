import asyncio
import os


from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

from app.db.config import create_db, drop_db, session_maker
from app.db.crud import notify_pending_users, fetch_and_send_unsent_post
from app.middlewares.db_session import DataBaseSession
from app.handlers.for_user import for_user_router
from app.comands_menu.bot_menu_cmds import bot_menu
from app.openai_assistant.queue import OpenAIRequestQueue
from app.payments.payment_routes import yookassa_webhook_handler





bot = Bot(token=os.getenv("TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(for_user_router)

openai_queue: OpenAIRequestQueue | None = None


# Константы
WEBHOOK_PATH = "/webhook"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 8000


async def on_startup(dispatcher: Dispatcher):
    print("GO bd")
    await bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True,
        allowed_updates=["message", "edited_message", "callback_query", "inline_query", "chosen_inline_result",
                         "callback_query", "shipping_query", "pre_checkout_query", "poll", "poll_answer",
                         "my_chat_member", "chat_member", "chat_join_request", "channel_post", "edited_channel_post"]
    )
    # await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
    await bot.set_my_description(description=f"✨ Представь, что у тебя есть доступ к мудрому собеседнику, который: "
                                             f"\n\n- Читал тысячи книг, статей и исследований "
                                             f"\n- Понимает, как устроено мышление и как работают твои убеждения "
                                             f"\n- Поможет поверить в себя и использовать силу "
                                             f"манифестации для материализации желаний "
                                             f"\n\n📚 В основе бота — учения Neville Goddard, Bob Proctor, Napoleon Hill, "
                                             f"Joe Dispenza, Вадима Зеланда и других мастеров "
                                             )
    await bot.set_my_short_description(short_description=f"Меня зовут Мария (можно Mari 🤗). Я разработала этого бота, "
                                                         f"чтобы помогать людям "
                                                         f"\n\nadmin: @RomanMo_admin")
    # await drop_db() # удаление Базы Данных
    await create_db() # создание Базы Данных
    global openai_queue
    openai_queue = OpenAIRequestQueue()
    await notify_pending_users(bot, session_maker)
    async with session_maker() as session:
        await fetch_and_send_unsent_post(bot, session)


async def on_shutdown(dispatcher: Dispatcher):
    print("on_shutdown")
    await bot.session.close()




async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.update.middleware(DataBaseSession(session_pool=session_maker)) # Middleware сессии БД
    # await bot.set_my_commands(scope=types.BotCommandScopeAllPrivateChats) #команда для удаления кнопки меню
    await bot.set_my_commands(commands=bot_menu, scope=types.BotCommandScopeAllPrivateChats())

    # 🌐 Создаём веб-приложение
    app = web.Application()

    async def health(request):
        return web.Response(text="ok")     #для проверки доступности контейнера и для Caddy
    app.router.add_get("/health", health)

    app.router.add_post("/yookassa/webhook", yookassa_webhook_handler)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_shutdown.append(on_shutdown)

    # 🚀 Запускаем aiohttp-сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=WEBAPP_HOST, port=WEBAPP_PORT)
    await site.start()

    print(f"Bot is running on {WEBAPP_HOST}:{WEBAPP_PORT}")
    print(f"Webhook URL: {WEBHOOK_URL}")

    # 🕒 Бесконечное ожидание (держим процесс живым)
    await asyncio.Event().wait()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")