import asyncio
import os


from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

from app.db.config import create_db, drop_db, session_maker
from app.middlewares.db_session import DataBaseSession
from app.handlers.for_user import for_user_router
from app.comands_menu.bot_menu_cmds import bot_menu
from app.openai_assistant.queue import OpenAIRequestQueue



bot = Bot(token=os.getenv("TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(for_user_router)

openai_queue: OpenAIRequestQueue | None = None


async def on_startup(dispatcher: Dispatcher):
    print("GO bd")
    await drop_db() # удаление Базы Данных
    await create_db() # создание Базы Данных
    global openai_queue
    openai_queue = OpenAIRequestQueue()



async def main():
    dp.startup.register(on_startup)
    dp.update.middleware(DataBaseSession(session_pool=session_maker)) # Middleware сессии БД
    await bot.delete_webhook(drop_pending_updates=True)
    # await bot.set_my_commands(scope=types.BotCommandScopeAllPrivateChats) #команда для удаления кнопки меню
    await bot.set_my_commands(commands=bot_menu, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")