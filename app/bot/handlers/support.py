from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.db import db_session
from app.services.driver_service import get_driver_by_telegram_id
from app.services.settings_service import get_setting

router = Router()


@router.message(F.text.in_(['📞 Оператор', '📞 Operator']))
async def support_contact(message: Message):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        lang = driver.language if driver else 'ru'
        support = get_setting(db, 'support_contact', '@support')
    text = f'Оператор Prime taxi: {support}' if lang == 'ru' else f'Prime taxi оператори: {support}'
    await message.answer(text, reply_markup=main_menu_keyboard(lang))
