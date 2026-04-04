from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards import LANGUAGE_KEYBOARD
from app.db import db_session
from app.services.driver_service import get_driver_by_telegram_id

router = Router()

LANG_TEXTS = {'ru': '🌐 Язык', 'uz_cyrl': '🌐 Тил'}


@router.message(F.text.in_(LANG_TEXTS.keys()) | (F.text == '🌐 Язык') | (F.text == '🌐 Тил'))
async def language_menu(message: Message):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if not driver:
            await message.answer('Используйте /start для привязки аккаунта.')
            return
    await message.answer('Выберите язык / Тилни танланг', reply_markup=LANGUAGE_KEYBOARD)
