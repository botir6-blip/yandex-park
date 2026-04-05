from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import cards_keyboard, main_menu_keyboard, single_card_actions
from app.bot.states import CardStates
from app.bot.texts import t
from app.db import db_session
from app.services.card_service import add_card, delete_card, get_active_cards, get_card, set_primary_card
from app.services.driver_service import get_driver_by_telegram_id, touch_driver

router = Router()


@router.message(F.text.in_(["💳 Мои карты", "💳 Карталарим"]))
async def cards_menu(message: Message):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if not driver:
            await message.answer("Используйте /start для привязки аккаунта Prime taxi.")
            return
        touch_driver(db, driver)
        db.commit()
        lang = driver.language or "ru"
        cards = get_active_cards(db, driver.id)
        if not cards:
            await message.answer(t(lang, "no_cards"), reply_markup=cards_keyboard([]))
            return
        await message.answer(t(lang, "cards_title"), reply_markup=cards_keyboard(cards))


@router.callback_query(F.data == "card:add")
async def card_add_start(callback: CallbackQuery, state: FSMContext):
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, callback.from_user.id)
        if not driver:
            await callback.message.answer("Используйте /start для привязки аккаунта Prime taxi.")
            await callback.answer()
            return
        lang = driver.language or "ru"

    await state.set_state(CardStates.waiting_for_card_number)
    await callback.message.answer(t(lang, "enter_card"))
    await callback.answer()


@router.message(CardStates.waiting_for_card_number)
async def card_number_received(message: Message, state: FSMContext):
    await state.update_data(card_number=message.text.strip())
    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        lang = driver.language if driver else "ru"
    await state.set_state(CardStates.waiting_for_holder_name)
    await message.answer(t(lang, "enter_holder"))


@router.message(CardStates.waiting_for_holder_name)
async def holder_received(message: Message, state: FSMContext):
    data = await state.get_data()
    holder = None if message.text.strip() == "-" else message.text.strip()

    with db_session() as db:
        driver = get_driver_by_telegram_id(db, message.from_user.id)
        if not driver:
            await message.answer("Используйте /start для привязки аккаунта Prime taxi.")
            await state.clear()
            return

        lang = driver.language or "ru"
        try:
            add_card(db, driver.id, data["card_number"], holder)
            db.commit()
            cards = get_active_cards(db, driver.id)
            await message.answer(t(lang, "card_added"), reply_markup=cards_keyboard(cards))
        except Exception as exc:
            await message.answer(str(exc), reply_markup=main_menu_keyboard(lang))

    await state.clear()


@router.callback_query(F.data.startswith("card:view:"))
async def card_view(callback: CallbackQuery):
    card_id = int(callback.data.rsplit(":", 1)[1])

    with db_session() as db:
        driver = get_driver_by_telegram_id(db, callback.from_user.id)
        if not driver:
            await callback.answer("Нет доступа", show_alert=True)
            return

        card = get_card(db, card_id, driver.id)
        if not card:
            await callback.answer("Карта не найдена", show_alert=True)
            return

        text = (
            f"<b>{card.card_mask}</b>\n"
            f"Тип: {card.card_type or 'Card'}\n"
            f"Владелец: {card.holder_name or '-'}"
        )

        await callback.message.answer(
            text,
            reply_markup=single_card_actions(card.id, card.is_primary),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data.startswith("card:primary:"))
async def card_make_primary(callback: CallbackQuery):
    card_id = int(callback.data.rsplit(":", 1)[1])

    with db_session() as db:
        driver = get_driver_by_telegram_id(db, callback.from_user.id)
        if not driver:
            await callback.answer("Нет доступа", show_alert=True)
            return

        try:
            set_primary_card(db, driver.id, card_id)
            db.commit()
            cards = get_active_cards(db, driver.id)
            await callback.message.answer("Основная карта обновлена.", reply_markup=cards_keyboard(cards))
        except Exception as exc:
            await callback.message.answer(str(exc))

    await callback.answer()


@router.callback_query(F.data.startswith("card:delete:"))
async def card_remove(callback: CallbackQuery):
    card_id = int(callback.data.rsplit(":", 1)[1])

    with db_session() as db:
        driver = get_driver_by_telegram_id(db, callback.from_user.id)
        if not driver:
            await callback.answer("Нет доступа", show_alert=True)
            return

        try:
            delete_card(db, driver.id, card_id)
            db.commit()
            cards = get_active_cards(db, driver.id)
            await callback.message.answer("Карта удалена.", reply_markup=cards_keyboard(cards))
        except Exception as exc:
            await callback.message.answer(str(exc))

    await callback.answer()
