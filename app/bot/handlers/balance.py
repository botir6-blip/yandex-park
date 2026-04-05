from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import t
from app.db import db_session
from app.services.driver_service import ensure_wallet, get_driver_by_telegram_id, touch_driver
from app.services.wallet_service import available_to_withdraw

router = Router()


@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if not driver:
            await message.answer("Используйте /start для привязки аккаунта Prime taxi.")
            return

        touch_driver(db, driver)
        wallet = ensure_wallet(db, driver)
        db.commit()
        lang = driver.language or "ru"

        text = (
            f"<b>{t(lang, 'balance_title')}</b>\n"
            f"Основной баланс: <b>{wallet.main_balance}</b>\n"
            f"Бонусный баланс: <b>{wallet.bonus_balance}</b>\n"
            f"Резерв: <b>{wallet.min_reserve_balance}</b>\n"
            f"Доступно к выводу: <b>{available_to_withdraw(wallet)}</b>"
        )

        await message.answer(text, reply_markup=main_menu_keyboard(lang), parse_mode="HTML")
