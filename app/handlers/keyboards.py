from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton




pay = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="1 запрос - 30р.", callback_data="pay30"),
     InlineKeyboardButton(text="20 запросов - 349р.", callback_data="pay349")],
     [InlineKeyboardButton(text="100 запросов - 1700р.", callback_data="pay1700")],
                                              ])