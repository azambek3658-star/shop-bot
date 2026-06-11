from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict
from config import config

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Каталог", callback_data="catalog")],
        [
            InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
        ],
        [InlineKeyboardButton(text="🎫 Поддержка", callback_data="support")]
    ])

def categories_kb(categories):
    buttons = [
        [InlineKeyboardButton(text=f"{c['emoji']} {c['name']}", callback_data=f"cat_{c['id']}")]
        for c in categories
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def products_kb(products, cat_id):
    buttons = []
    for p in products:
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{stock_icon} {p['name']} — {p['price']} ₽",
            callback_data=f"product_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_detail_kb(product_id, in_stock):
    buttons = []
    if in_stock:
        buttons.append([InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="❌ Нет в наличии", callback_data="no_stock")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_methods_kb(product_id, price_rub, price_stars):
    buttons = []
    if config.STARS_ENABLED and price_stars:
        buttons.append([InlineKeyboardButton(
            text=f"⭐ Telegram Stars ({price_stars} Stars)",
            callback_data=f"pay_stars_{product_id}"
        )])
    if config.YOOKASSA_ENABLED:
        buttons.append([InlineKeyboardButton(
            text=f"💳 Карта RUB ({price_rub} ₽)",
            callback_data=f"pay_kassa_{product_id}_RUB"
        )])
        buttons.append([InlineKeyboardButton(
            text=f"💳 Карта KZT (~{round(price_rub / 0.22)} ₸)",
            callback_data=f"pay_kassa_{product_id}_KZT"
        )])
        buttons.append([InlineKeyboardButton(
            text=f"💳 Карта UAH (~{round(price_rub * 0.35)} ₴)",
            callback_data=f"pay_kassa_{product_id}_UAH"
        )])
    if config.CRYPTOBOT_ENABLED:
        buttons.append([
            InlineKeyboardButton(text="💎 TON", callback_data=f"pay_crypto_{product_id}_TON"),
            InlineKeyboardButton(text="💵 USDT", callback_data=f"pay_crypto_{product_id}_USDT")
        ])
    if config.STEAM_ENABLED:
        buttons.append([InlineKeyboardButton(
            text="🎮 Steam скины",
            callback_data=f"pay_steam_{product_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"product_{product_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def my_orders_kb(orders):
    buttons = []
    for o in orders[:10]:
        status_icon = "✅" if o["status"] == "completed" else "⏳"
        buttons.append([InlineKeyboardButton(
            text=f"{status_icon} #{o['id']} {o['product_name']} — {o['total_price']} {o['currency']}",
            callback_data=f"order_detail_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
