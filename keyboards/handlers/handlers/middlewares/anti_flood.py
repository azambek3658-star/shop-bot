import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.0):
        self.limit = limit
        self._last_call: Dict[int, float] = {}

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None
        if user_id:
            now = time.monotonic()
            last = self._last_call.get(user_id, 0)
            if now - last < self.limit:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Не так быстро!")
                return
            self._last_call[user_id] = now
        return await handler(event, data)
