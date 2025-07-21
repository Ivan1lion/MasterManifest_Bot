from aiogram.types import BotCommand


bot_menu = [
    BotCommand(command="start", description="🔄Перезапуск"),
    BotCommand(command="info", description="🤖Как пользоваться ботом"),
    BotCommand(command="balance", description="⭐️Баланс (кол-во запросов)"),
    BotCommand(command="privacy", description="☑️Политика конфиденциальности"),
    BotCommand(command="offer", description="📜Оферта"),
]