from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import Database
from keyboards.user_kb import (
    main_menu_kb, categories_kb,
    payment_methods_kb, confirm_order_kb, my_orders_kb
)

router = Router()

class OrderStates(StatesGroup):
    choosing_category = State()
    entering_age = State()
    choosing_payment = State()

CATEGORIES = {
    "cat_tg": "💬 Telegram аккаунты",
    "cat_social": "📱 Соцсети",
    "cat_streaming": "🎵 Стриминг",
    "cat_forums": "💬 Форумы",
    "cat_other": "🌐 Другое"
}

@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    if user["banned"]:
        return await message.answer("🚫 Вы заблокированы.")
    welcome = await db.get_setting("welcome_text", "👋 Добро пожаловать!")
    shop_open = await db.get_setting("shop_open", "1")
    text = f"{welcome}\n\n"
    if shop_open != "1":
        text += "⚠️ <b>Магазин временно закрыт.</b>"
    else:
        text += "Выберите раздел:"
    await message.answer(text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "buy_start")
async def buy_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.choosing_category)
    await call.message.edit_text(
        "📂 <b>Выберите категорию аккаунта:</b>",
        reply_markup=categories_kb()
    )

@router.callback_query(OrderStates.choosing_category, F.data.startswith("cat_"))
async def choose_category(call: CallbackQuery, state: FSMContext):
    category = CATEGORIES.get(call.data, "Другое")
    await state.update_data(category=category)
    await state.set_state(OrderStates.entering_age)
    await call.message.edit_text(
        f"✅ Категория: <b>{category}</b>\n\n"
        f"⏳ Напишите желаемый отлег аккаунта:\n\n"
        f"Например: <i>от 2 до 5 лет</i> или <i>не менее 3 лет</i>"
    )

@router.message(OrderStates.entering_age)
async def enter_age(message: Message, state: FSMContext):
    await state.update_data(age_request=message.text.strip())
    await state.set_state(OrderStates.choosing_payment)
    data = await state.get_data()
    await message.answer(
        f"✅ Категория: <b>{data['category']}</b>\n"
        f"✅ Отлег: <b>{data['age_request']}</b>\n\n"
        f"💳 <b>Выберите способ оплаты:</b>",
        reply_markup=payment_methods_kb()
    )

@router.callback_query(OrderStates.choosing_payment, F.data.startswith("pay_"))
async def choose_payment(call: CallbackQuery, state: FSMContext):
    payment_map = {
        "pay_stars": "⭐ Telegram Stars",
        "pay_ton": "💎 TON",
        "pay_usdt": "💵 USDT",
        "pay_steam": "🎮 Steam скины"
    }
    payment = payment_map.get(call.data, call.data)
    await state.update_data(payment_method=payment)
    data = await state.get_data()
    await call.message.edit_text(
        f"📋 <b>Ваша заявка:</b>\n\n"
        f"📂 Категория: <b>{data['category']}</b>\n"
        f"⏳ Отлег: <b>{data['age_request']}</b>\n"
        f"💳 Оплата: <b>{payment}</b>\n\n"
        f"Всё верно? Отправляем заявку?",
        reply_markup=confirm_order_kb()
    )

@router.callback_query(F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    await state.clear()
    order_id = await db.create_order(
        call.from_user.id,
        data["category"],
        data["age_request"],
        data["payment_method"]
    )
    await call.message.edit_text(
        f"✅ <b>Заявка #{order_id} отправлена!</b>\n\n"
        f"Ожидайте — администратор подберёт аккаунт и пришлёт ссылку на оплату.\n\n"
        f"Обычно до 30 минут."
    )

@router.callback_query(F.data == "my_orders")
async def my_orders(call: CallbackQuery, db: Database):
    orders = await db.get_user_orders(call.from_user.id)
    if not orders:
        return await call.answer("Заказов нет", show_alert=True)
    await call.message.edit_text("📋 <b>Ваши заказы:</b>", reply_markup=my_orders_kb(orders))

@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext, db: Database):
    await state.clear()
    welcome = await db.get_setting("welcome_text", "👋 Добро пожаловать!")
    await call.message.edit_text(welcome + "\n\nВыберите раздел:", reply_markup=main_menu_kb())

@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery, db: Database):
    orders = await db.get_user_orders(call.from_user.id, limit=100)
    completed = [o for o in orders if o["status"] == "completed"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text(
        f"👤 <b>Профиль</b>\n\n"
        f"ID: <code>{call.from_user.id}</code>\n"
        f"Заказов выполнено: {len(completed)}",
        reply_markup=kb
    )    
