from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import Database
from config import config

router = Router()

class SupportStates(StatesGroup):
    waiting_message = State()

@router.callback_query(F.data == "support")
async def support_menu(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать в поддержку", callback_data="support_write")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    text = "🎫 <b>Поддержка</b>\n\nОпишите проблему и мы поможем!"
    if config.SUPPORT_USERNAME:
        text += f"\n\nИли напишите напрямую: @{config.SUPPORT_USERNAME}"
    await call.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "support_write")
async def support_write(call: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_message)
    await call.message.edit_text("✍️ Опишите вашу проблему:")

@router.message(SupportStates.waiting_message)
async def support_received(message: Message, state: FSMContext, db: Database):
    ticket_id = await db.create_ticket(message.from_user.id, message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ Тикет #{ticket_id} создан!\nОтветим в ближайшее время.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main")]
        ])
    )
