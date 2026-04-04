from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.states import WithdrawalStates
from app.bot.texts import t
from app.db import db_session
from app.services.card_service import get_active_cards
from app.services.driver_service import ensure_wallet, get_driver_by_telegram_id, touch_driver
from app.services.withdrawal_service import create_withdrawal_request, get_open_withdrawal
from app.services.wallet_service import available_to_withdraw

router = Router()


@router.message(F.text.in_(['💸 Вывод средств', '💸 Пул ечиш']))
async def withdrawal_start(message: Message, state: FSMContext):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if not driver:
            await message.answer('Используйте /start для привязки аккаунта.')
            return
        touch_driver(db, driver)
        lang = driver.language or 'ru'
        cards = get_active_cards(db, driver.id)
        if not cards:
            await message.answer(t(lang, 'withdraw_no_card'), reply_markup=main_menu_keyboard(lang))
            return
        open_req = get_open_withdrawal(db, driver.id)
        if open_req:
            await message.answer('У вас уже есть открытая заявка на вывод.', reply_markup=main_menu_keyboard(lang))
            return
        wallet = ensure_wallet(db, driver)
        await state.set_state(WithdrawalStates.waiting_for_amount)
        await message.answer(
            f"{t(lang, 'withdraw_enter_amount')}
Доступно: <b>{available_to_withdraw(wallet)}</b>",
            reply_markup=main_menu_keyboard(lang),
        )


@router.message(WithdrawalStates.waiting_for_amount)
async def withdrawal_amount(message: Message, state: FSMContext):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if not driver:
            await message.answer('Используйте /start для привязки аккаунта.')
            await state.clear()
            return
        lang = driver.language or 'ru'
        cards = get_active_cards(db, driver.id)
        primary = next((c for c in cards if c.is_primary), cards[0] if cards else None)
        if not primary:
            await message.answer(t(lang, 'withdraw_no_card'), reply_markup=main_menu_keyboard(lang))
            await state.clear()
            return
        try:
            amount = Decimal(message.text.replace(',', '.').strip())
            create_withdrawal_request(db, driver, primary.id, amount)
            await message.answer(t(lang, 'withdraw_created'), reply_markup=main_menu_keyboard(lang))
        except Exception as exc:
            await message.answer(str(exc), reply_markup=main_menu_keyboard(lang))
        await state.clear()
