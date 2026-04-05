from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import LANGUAGE_KEYBOARD, main_menu_keyboard, phone_request_keyboard
from app.bot.states import RegistrationStates
from app.bot.texts import t
from app.db import db_session
from app.services.driver_service import bind_driver_to_telegram, get_driver_by_phone, get_driver_by_telegram_id, touch_driver

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if driver:
            touch_driver(db, driver)
            lang = driver.language or 'ru'
            await state.clear()
            await message.answer(t(lang, 'main_menu'), reply_markup=main_menu_keyboard(lang))
            return
    await state.clear()
    await message.answer('Здравствуйте. Добро пожаловать в Prime taxi. Выберите язык / Prime taxi га хуш келибсиз. Тилни танланг.', reply_markup=LANGUAGE_KEYBOARD)


@router.callback_query(F.data.startswith('lang:'))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(':', 1)[1]
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, callback.from_user.id)
        if driver:
            driver.language = lang
            touch_driver(db, driver)
            text = 'Язык Prime taxi обновлен.' if lang == 'ru' else 'Prime taxi тили янгиланди.'
            await state.clear()
            await callback.message.answer(text, reply_markup=main_menu_keyboard(lang))
        else:
            await state.update_data(selected_lang=lang)
            await state.set_state(RegistrationStates.waiting_for_phone)
            await callback.message.answer(t(lang, 'share_phone'), reply_markup=phone_request_keyboard())
    await callback.answer()


@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def receive_contact(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('selected_lang', 'ru')
    phone = message.contact.phone_number

    with db_session() as db:
        existing = get_driver_by_telegram_id(db, message.from_user.id)
        if existing:
            touch_driver(db, existing)
            await state.clear()
            await message.answer(t(existing.language or 'ru', 'main_menu'), reply_markup=main_menu_keyboard(existing.language or 'ru'))
            return

        driver = get_driver_by_phone(db, phone)
        if not driver:
            await message.answer(t(lang, 'not_found'))
            return
        if driver.telegram_id and driver.telegram_id != message.from_user.id:
            await message.answer(t(lang, 'already_bound_other'))
            return

        bind_driver_to_telegram(db, driver, message.from_user.id, message.from_user.username)
        driver.language = lang
        await state.clear()
        await message.answer(t(lang, 'bound_ok'), reply_markup=main_menu_keyboard(lang))


@router.message(RegistrationStates.waiting_for_phone)
async def waiting_for_phone_text(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('selected_lang', 'ru')
    await message.answer(t(lang, 'share_phone'), reply_markup=phone_request_keyboard())
