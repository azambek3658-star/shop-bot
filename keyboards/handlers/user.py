from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database.db import Database
from keyboards.user_kb import (
    main_menu_kb, categories_kb, products_kb,
    product_detail_kb, payment_methods_kb, my_orders_kb
)

router = Router()

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

@router.callback_query(F.data == "catalog")
async def show_catalog(call: CallbackQuery, db: Database):
    categories = await db.get_categories()
    if not categories:
        return await call.answer("Каталог пуст", show_alert=True)
    await call.message.edit_text("📂 <b>Категории:</b>", reply_markup=categories_kb(categories))

@router.callback_query(F.data.startswith("cat_"))
async def show_products(call: CallbackQuery, db: Database):
    cat_id = int(call.data.split("_")[1])
    products = await db.get_products(category_id=cat_id)
    for p in products:
        p["stock"] = await db.get_stock_count(p["id"])
    if not products:
        return await call.answer("Нет товаров", show_alert=True)
    await call.message.edit_text("🛍 <b>Товары:</b>", reply_markup=products_kb(products, cat_id))

@router.callback_query(F.data.startswith("product_"))
async def show_product(call: CallbackQuery, db: Database):
    product_id = int(call.data.split("_")[1])
    product = await db.get_product(product_id)
    if not product:
        return await call.answer("Товар не найден", show_alert=True)
    stock = await db.get_stock_count(product_id)
    stars = f"\n⭐ {product['price_stars']} Stars" if product["price_stars"] else ""
    text = (
        f"<b>{product['name']}</b>\n\n"
        f"{product['description'] or ''}\n\n"
        f"💰 Цена: <b>{product['price']} ₽</b>{stars}\n"
        f"📦 В наличии: <b>{stock} шт.</b>"
    )
    await call.message.edit_text(text, reply_markup=product_detail_kb(product_id, stock > 0))

@router.callback_query(F.data.startswith("buy_"))
async def choose_payment(call: CallbackQuery, db: Database):
    product_id = int(call.data.split("_")[1])
    product = await db.get_product(product_id)
    if not product:
        return await call.answer("Товар не найден", show_alert=True)
    stock = await db.get_stock_count(product_id)
    if stock == 0:
        return await call.answer("❌ Товар закончился", show_alert=True)
    await call.message.edit_text(
        f"💳 <b>Оплата:</b> {product['name']}\n\nВыберите способ:",
        reply_markup=payment_methods_kb(product_id, product["price"], product["price_stars"])
    )

@router.callback_query(F.data == "my_orders")
async def my_orders(call: CallbackQuery, db: Database):
    orders = await db.get_user_orders(call.from_user.id)
    if not orders:
        return await call.answer("Заказов нет", show_alert=True)
    await call.message.edit_text("📋 <b>Ваши заказы:</b>", reply_markup=my_orders_kb(orders))

@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, db: Database):
    welcome = await db.get_setting("welcome_text", "👋 Добро пожаловать!")
    await call.message.edit_text(welcome + "\n\nВыберите раздел:", reply_markup=main_menu_kb())

@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery, db: Database):
    orders = await db.get_user_orders(call.from_user.id, limit=100)
    completed = [o for o in orders if o["status"] == "completed"]
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text(
        f"👤 <b>Профиль</b>\n\n"
        f"ID: <code>{call.from_user.id}</code>\n"
        f"Заказов: {len(completed)}\n"
        f"Потрачено: {sum(o['total_price'] for o in completed):.2f} ₽",
        reply_markup=kb
      )
