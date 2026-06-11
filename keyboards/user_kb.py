from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить аккаунт", callback_data="buy_start")],
        [
            InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
        ],
        [InlineKeyboardButton(text="🎫 Поддержка", callback_data="support")]
    ])

def categories_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Telegram аккаунты", callback_data="cat_games")],
        [InlineKeyboardButton(text="📱 Соцсети", callback_data="cat_social")],
        [InlineKeyboardButton(text="🎵 Стриминг", callback_data="cat_streaming")],
        [InlineKeyboardButton(text="💬 Форумы", callback_data="cat_forums")],
        [InlineKeyboardButton(text="🌐 Другое", callback_data="cat_other")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

def payment_methods_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_stars")],
        [
            InlineKeyboardButton(text="💎 TON", callback_data="pay_ton"),
            InlineKeyboardButton(text="💵 USDT", callback_data="pay_usdt")
        ],
        [InlineKeyboardButton(text="🎮 Steam скины", callback_data="pay_steam")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="buy_start")]
    ])

def confirm_order_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить заявку", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")]
    ])

def my_orders_kb(orders):
    buttons = []
    for o in orders[:10]:
        status_icon = "✅" if o["status"] == "completed" else "⏳" if o["status"] == "pending" else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status_icon} #{o['id']} {o['category']} — {o['payment_method']}",
            callback_data=f"order_detail_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
