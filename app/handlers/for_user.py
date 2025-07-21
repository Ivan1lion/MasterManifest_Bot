from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, CallbackQuery, InputMediaPhoto, PreCheckoutQuery, ContentType, SuccessfulPayment


from handlers.text_for_user import text_privacy, text_offer

for_user_router = Router()




# команды для кнопки МЕНЮ

@for_user_router.message(Command("balance"))
async def policy_cmd(message: Message):
    await message.answer(f"обращение в БД с проверкой оставщегося кол-ва запросов")


@for_user_router.message(Command("privacy"))
async def policy_cmd(message: Message):
    await message.answer(text_privacy)


@for_user_router.message(Command("offer"))
async def offer_cmd(message: Message):
    await message.answer(text_offer)


@for_user_router.message(CommandStart())
async def cmd_start(message: Message):
    file = FSInputFile("./mediafile_for_bot/start.jpg")
    string = (f"📖 Что такое @MasterManifest_Bot и как он поможет вам?"
              f"\n\nПредставьте, что у вас есть доступ к мудрому собеседнику, который:"
              f"\n\n✨ Читал тысячи книг, статей и исследований"
              f"\n✨ Понимает, как устроено мышление и как работают ваши убеждения"
              f"\n✨ Может помочь вам изменить мышление, поверить в себя и научиться использовать силу манифестации"
              f"\n\nЭто и есть @MasterManifest_Bot — умный виртуальный помощник, созданный с помощью технологий "
              f"искусственного интеллекта. Он умеет понимать ваши вопросы и давать ответы простым, понятным языком — без осуждения "
              f"и лишней теории\n"
              f"\nНо самое главное — этот бот обучен специально, чтобы помогать людям в таких темах, как:\n"
              f"\n💭 Материализация желаний"
              f"\n🧘‍♀️ Сила мысли и трансформация мышления"
              f"\n💎 Философия богатства"
              f"\n🌌 Закон притяжения"
              f"\n🌱 Работа с подсознанием и внутренними установками\n"
              f"\nПросто напишите свой вопрос — и получите ответ, вдохновение или пошаговый совет, как изменить свою "
              f"реальность через мысли и чувства")
    await message.answer(text=string)





    ###################################################################################################################
    ################################################### ОБРАБОТЧИКИ ###################################################
    ###################################################################################################################

    @for_user_router.message(F.photo | F.video | F.animation | F.sticker | F.voice | F.document | F.audio | F.video_note)
    async def filter(message: Message):
        await message.delete()
        await message.answer("Запросы только в формате текста")