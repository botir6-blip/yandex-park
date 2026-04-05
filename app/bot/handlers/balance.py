from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.texts import t
from app.db import db_session
from app.services.driver_service import ensure_wallet, get_driver_by_telegram_id, touch_driver
from app.services.wallet_service import available_to_withdraw
from app.services.yandex_service import YandexFleetError, get_driver_balance, is_enabled as yandex_enabled

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
        lang = driver.language or "ru"

        lines = [f"<b>{t(lang, 'balance_title')}</b>"]

        if yandex_enabled():
            try:
                yb = get_driver_balance(driver, auto_link=True)
                if yb.ok:
                    lines.extend([
                        "",
                        "<b>Яндекс баланс</b>",
                        f"Текущий баланс: <b>{yb.balance or '0'}</b> {yb.currency or ''}".rstrip(),
                    ])
                    if yb.profile_id:
                        lines.append(f"ID профиля: <code>{yb.profile_id}</code>")
                else:
                    lines.extend(["", f"<i>{yb.note}</i>"])
            except YandexFleetError as exc:
                lines.extend(["", f"<i>Не удалось получить баланс из Яндекса: {str(exc)}</i>"])

        lines.extend([
            "",
            "<b>Внутренний баланс бота</b>",
            f"Основной баланс: <b>{wallet.main_balance}</b>",
            f"Бонусный баланс: <b>{wallet.bonus_balance}</b>",
            f"Резерв: <b>{wallet.min_reserve_balance}</b>",
            f"Доступно к выводу: <b>{available_to_withdraw(wallet)}</b>",
        ])

        db.commit()
        await message.answer("\n".join(lines), reply_markup=main_menu_keyboard(lang), parse_mode="HTML")
