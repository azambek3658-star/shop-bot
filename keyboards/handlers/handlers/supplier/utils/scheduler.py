import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database.db import Database
from config import config

logger = logging.getLogger(__name__)

async def check_pending_orders(bot: Bot, db: Database):
    rows = await db.fetchall(
        "SELECT * FROM orders WHERE status='pending' AND created_at < datetime('now', '-1 hour')"
    )
    for row in rows:
        order = dict(row)
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"⚠️ Заявка #{order['id']} висит уже час без ответа!\n"
                    f"Клиент: {order['user_id']}\n"
                    f"Категория: {order['category']}"
                )
            except Exception:
                pass

def start_scheduler(bot: Bot, db: Database) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_pending_orders,
        "interval",
        minutes=30,
        kwargs={"bot": bot, "db": db}
    )
    return scheduler
