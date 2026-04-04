from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

LANGUAGE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="Ўзбекча (кирилл)", callback_data="lang:uz_cyrl")],
    ]
)


def phone_request_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Телефонни юбориш / Отправить телефон", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(lang: str = "ru"):
    if lang == "uz_cyrl":
        rows = [
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="💳 Карталарим")],
            [KeyboardButton(text="💸 Пул ечиш"), KeyboardButton(text="📜 Тарих")],
            [KeyboardButton(text="🌐 Тил"), KeyboardButton(text="📞 Оператор")],
        ]
    else:
        rows = [
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="💳 Мои карты")],
            [KeyboardButton(text="💸 Вывод средств"), KeyboardButton(text="📜 История")],
            [KeyboardButton(text="🌐 Язык"), KeyboardButton(text="📞 Оператор")],
        ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cards_keyboard(cards):
    builder = InlineKeyboardBuilder()
    for card in cards:
        title = f"{'⭐ ' if card.is_primary else ''}{card.card_mask} ({card.card_type or 'Card'})"
        builder.button(text=title, callback_data=f"card:view:{card.id}")
    builder.button(text="➕ Добавить карту", callback_data="card:add")
    builder.adjust(1)
    return builder.as_markup()


def single_card_actions(card_id: int, is_primary: bool):
    builder = InlineKeyboardBuilder()
    if not is_primary:
        builder.button(text="⭐ Сделать основной", callback_data=f"card:primary:{card_id}")
    builder.button(text="🗑 Удалить", callback_data=f"card:delete:{card_id}")
    builder.adjust(1)
    return builder.as_markup()
