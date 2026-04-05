from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import t
from app.db import db_session
from app.services.driver_service import get_driver_by_telegram_id, touch_driver

router = Router()


def _driver_context(telegram_user):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, telegram_user.id)
        if driver:
            touch_driver(db, driver)
            db.commit()
            lang = driver.language or 'ru'
            return driver, lang
    return None, 'ru'


@router.message(Command('menu'))
async def cmd_menu(message: Message):
    driver, lang = _driver_context(message.from_user)
    if not driver:
        await message.answer('Сначала используйте /start и привяжите аккаунт Prime taxi.')
        return
    await message.answer(t(lang, 'main_menu'), reply_markup=main_menu_keyboard(lang))


@router.message()
async def fallback(message: Message):
    driver, lang = _driver_context(message.from_user)
    if not driver:
        await message.answer('Используйте /start для привязки аккаунта Prime taxi.')
        return
    await message.answer(t(lang, 'main_menu'), reply_markup=main_menu_keyboard(lang))
