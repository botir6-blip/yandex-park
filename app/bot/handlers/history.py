from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import t
from app.db import db_session
from app.services.driver_service import get_driver_by_telegram_id, touch_driver
from app.services.transaction_service import get_driver_transactions

router = Router()


@router.message(F.text.in_(["📜 История", "📜 Тарих"]))
async def show_history(message: Message):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if not driver:
            await message.answer("Используйте /start для привязки аккаунта Prime taxi.")
            return

        touch_driver(db, driver)
        lang = driver.language or "ru"
        txs = get_driver_transactions(db, driver.id, 10)

        if not txs:
            await message.answer("Операций пока нет.", reply_markup=main_menu_keyboard(lang))
            return

        lines = [f"<b>{t(lang, 'history_title')}</b>"]
        for tx in txs:
            dt = tx.created_at.strftime("%Y-%m-%d %H:%M") if tx.created_at else ""
            lines.append(f"• {dt} — {tx.type} — {tx.amount}")

        await message.answer(
            "\n".join(lines),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )
