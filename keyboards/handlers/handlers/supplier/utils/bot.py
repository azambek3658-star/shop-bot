import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database.db import Database
from middlewares.anti_flood import AntiFloodMiddleware
from handlers import user, admin, support
from utils.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    db = Database()
    await db.init()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.middleware(AntiFloodMiddleware(limit=1.0))
    dp.callback_query.middleware(AntiFloodMiddleware(limit=0.5))

    dp["db"] = db
    dp["bot"] = bot

    dp.include_router(admin.router)
    dp.include_router(support.router)
    dp.include_router(user.router)

    scheduler = start_scheduler(bot, db)
    scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
