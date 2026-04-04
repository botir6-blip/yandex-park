import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import balance, cards, common, history, language, start, support, withdrawals
from app.config import settings


async def run_bot():
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN берилмаган. .env ни тўлдиринг.")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(balance.router)
    dp.include_router(cards.router)
    dp.include_router(withdrawals.router)
    dp.include_router(history.router)
    dp.include_router(support.router)
    dp.include_router(language.router)
    dp.include_router(common.router)

    await dp.start_polling(bot)


def main():
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
