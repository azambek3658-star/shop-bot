import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import Database
from config import config

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

class AdminStates(StatesGroup):
    broadcast_text = State()
    edit_welcome = State()
    reply_ticket = State()

def admin_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Заявки", callback_data="adm_orders"),
            InlineKeyboardButton(text="🎫 Тикеты", callback_data="adm_tickets")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="adm_settings")
        ],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users")]
    ])

@router.message(Command("admin"))
async def admin_panel(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    users = await db.get_user_count()
    orders_today = await db.get_orders_today()
    tickets = await db.get_open_tickets()
    await message.answer(
        f"⚙️ <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"📦 Заказов сегодня: <b>{orders_today}</b>\n"
        f"🎫 Открытых тикетов: <b>{len(tickets)}</b>",
        reply_markup=admin_main_kb()
    )

@router.callback_query(F.data == "adm_orders")
async def adm_orders(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    rows = await db.fetchall("SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20")
    orders = [dict(r) for r in rows]
    if not orders:
        return await call.answer("Новых заявок нет", show_alert=True)
    buttons = []
    for o in orders:
        buttons.append([InlineKeyboardButton(
            text=f"#{o['id']} | {o['category']} | {o['age_request'][:15]}",
            callback_data=f"adm_order_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back")])
    await call.message.edit_text("📋 <b>Новые заявки:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("adm_order_"))
async def adm_order_detail(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split("_")[2])
    order = await db.get_order(order_id)
    if not order:
        return await call.answer("Не найдено")
    user = await db.get_user(order["user_id"])
    username = f"@{user['username']}" if user and user.get("username") else str(order["user_id"])
    text = (
        f"📋 <b>Заявка #{order_id}</b>\n\n"
        f"👤 Клиент: {username} (<code>{order['user_id']}</code>)\n"
        f"📂 Категория: <b>{order['category']}</b>\n"
        f"⏳ Отлег: <b>{order['age_request']}</b>\n"
        f"💳 Оплата: <b>{order['payment_method']}</b>\n"
        f"📅 Дата: {order['created_at'][:16]}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Отправить ссылку оплаты", callback_data=f"adm_sendlink_{order_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_{order_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm_orders")]
    ])
    await call.message.edit_text(text, reply_markup=kb)

class SendLinkStates(StatesGroup):
    waiting_link = State()

@router.callback_query(F.data.startswith("adm_sendlink_"))
async def adm_sendlink(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split("_")[2])
    await state.update_data(send_link_order_id=order_id)
    await state.set_state(SendLinkStates.waiting_link)
    await call.message.edit_text(
        f"💳 Отправьте ссылку на оплату для заявки #{order_id}:\n\n"
        f"Просто скопируйте и вставьте ссылку:"
    )

@router.message(SendLinkStates.waiting_link)
async def adm_send_link(message: Message, state: FSMContext, db: Database, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    order_id = data["send_link_order_id"]
    link = message.text.strip()
    await state.clear()
    order = await db.get_order(order_id)
    if not order:
        return await message.answer("Заказ не найден")
    await db.update_order(order_id, status="waiting_payment", payment_link=link)
    try:
        await bot.send_message(
            order["user_id"],
            f"✅ <b>Ваша заявка #{order_id} одобрена!</b>\n\n"
            f"📂 Категория: <b>{order['category']}</b>\n"
            f"⏳ Отлег: <b>{order['age_request']}</b>\n"
            f"💳 Способ оплаты: <b>{order['payment_method']}</b>\n\n"
            f"💳 <b>Ссылка для оплаты:</b>\n{link}\n\n"
            f"После оплаты аккаунт будет выдан автоматически."
        )
        await message.answer(f"✅ Ссылка отправлена клиенту!", reply_markup=admin_main_kb())
    except Exception:
        await message.answer("❌ Не удалось отправить клиенту. Возможно заблокировал бота.")

@router.callback_query(F.data.startswith("adm_reject_"))
async def adm_reject(call: CallbackQuery, db: Database, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split("_")[2])
    order = await db.get_order(order_id)
    await db.update_order(order_id, status="rejected")
    try:
        await bot.send_message(order["user_id"], f"❌ Заявка #{order_id} отклонена. Обратитесь в поддержку.")
    except Exception:
        pass
    await call.answer("Отклонено")
    await adm_orders(call, db)

@router.callback_query(F.data == "adm_tickets")
async def adm_tickets(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    tickets = await db.get_open_tickets()
    if not tickets:
        return await call.answer("Открытых тикетов нет", show_alert=True)
    buttons = [
        [InlineKeyboardButton(
            text=f"#{t['id']} от @{t['username'] or t['user_id']}",
            callback_data=f"adm_ticket_{t['id']}"
        )] for t in tickets
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back")])
    await call.message.edit_text("🎫 Открытые тикеты:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("adm_ticket_"))
async def adm_ticket_detail(call: CallbackQuery, db: Database, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    ticket_id = int(call.data.split("_")[2])
    rows = await db.fetchall("SELECT * FROM support_tickets WHERE id=?", (ticket_id,))
    if not rows:
        return
    t = dict(rows[0])
    await state.update_data(reply_ticket_id=ticket_id, reply_user_id=t["user_id"])
    await state.set_state(AdminStates.reply_ticket)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть без ответа", callback_data=f"adm_ticket_close_{ticket_id}")]
    ])
    await call.message.edit_text(
        f"🎫 Тикет #{ticket_id}\nОт: {t['user_id']}\n\n{t['message']}\n\nОтправьте ответ:",
        reply_markup=kb
    )

@router.message(AdminStates.reply_ticket)
async def adm_reply_ticket(message: Message, state: FSMContext, db: Database, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await db.close_ticket(data["reply_ticket_id"], message.text.strip())
    await state.clear()
    try:
        await bot.send_message(data["reply_user_id"], f"📩 <b>Ответ поддержки:</b>\n\n{message.text.strip()}")
    except Exception:
        pass
    await message.answer("✅ Ответ отправлен!", reply_markup=admin_main_kb())

@router.callback_query(F.data.startswith("adm_ticket_close_"))
async def adm_ticket_close(call: CallbackQuery, db: Database, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    ticket_id = int(call.data.split("_")[3])
    await db.close_ticket(ticket_id)
    await state.clear()
    await call.answer("Закрыто")
    await adm_tickets(call, db)

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await call.message.edit_text("Введите текст рассылки:")

@router.message(AdminStates.broadcast_text)
async def adm_broadcast_send(message: Message, state: FSMContext, db: Database, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    users = await db.get_all_users()
    sent, failed = 0, 0
    for user in users:
        if user["banned"]:
            continue
        try:
            await bot.send_message(user["tg_id"], message.text.strip())
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"📢 Готово!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}", reply_markup=admin_main_kb())

@router.callback_query(F.data == "adm_settings")
async def adm_settings(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    shop_open = await db.get_setting("shop_open", "1")
    status = "✅ Открыт" if shop_open == "1" else "❌ Закрыт"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Магазин: {status}", callback_data="adm_toggle_shop")],
        [InlineKeyboardButton(text="✏️ Приветствие", callback_data="adm_edit_welcome")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back")]
    ])
    await call.message.edit_text("⚙️ Настройки:", reply_markup=kb)

@router.callback_query(F.data == "adm_toggle_shop")
async def adm_toggle_shop(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    current = await db.get_setting("shop_open", "1")
    await db.set_setting("shop_open", "0" if current == "1" else "1")
    await call.answer("Статус изменён")
    await adm_settings(call, db)

@router.callback_query(F.data == "adm_edit_welcome")
async def adm_edit_welcome(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.edit_welcome)
    await call.message.edit_text("Введите новый текст приветствия:")

@router.message(AdminStates.edit_welcome)
async def adm_save_welcome(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id):
        return
    await db.set_setting("welcome_text", message.text.strip())
    await state.clear()
    await message.answer("✅ Приветствие обновлено!", reply_markup=admin_main_kb())

@router.callback_query(F.data == "adm_users")
async def adm_users(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    users = await db.get_all_users()
    await call.message.edit_text(
        f"👥 Всего: {len(users)}\n\n/ban [id] — заблокировать\n/unban [id] — разблокировать",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back")]])
    )

@router.message(Command("ban"))
async def cmd_ban(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Использование: /ban [user_id]")
    await db.ban_user(int(parts[1]), True)
    await message.answer(f"✅ Пользователь {parts[1]} заблокирован.")

@router.message(Command("unban"))
async def cmd_unban(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Использование: /unban [user_id]")
    await db.ban_user(int(parts[1]), False)
    await message.answer(f"✅ Пользователь {parts[1]} разблокирован.")

@router.callback_query(F.data == "adm_back")
async def adm_back(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    users = await db.get_user_count()
    orders_today = await db.get_orders_today()
    tickets = await db.get_open_tickets()
    await call.message.edit_text(
        f"⚙️ <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"📦 Заказов сегодня: <b>{orders_today}</b>\n"
        f"🎫 Открытых тикетов: <b>{len(tickets)}</b>",
        reply_markup=admin_main_kb()
  )
