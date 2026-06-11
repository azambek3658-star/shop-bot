import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message, LabeledPrice,
    PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from database.db import Database
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars(call: CallbackQuery, db: Database, bot: Bot):
    product_id = int(call.data.split("_")[2])
    product = await db.get_product(product_id)
    if not product or not product["price_stars"]:
        return await call.answer("Оплата Stars недоступна", show_alert=True)
    stock = await db.get_stock_count(product_id)
    if stock == 0:
        return await call.answer("❌ Товар закончился", show_alert=True)
    order_id = await db.create_order(
        call.from_user.id, product_id, 1,
        product["price_stars"], "XTR", "stars"
    )
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=product["name"],
        description=product["description"] or product["name"],
        payload=f"order_{order_id}",
        currency="XTR",
        prices=[LabeledPrice(label=product["name"], amount=product["price_stars"])],
        provider_token=""
    )
    await call.answer()

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, db: Database):
    order_id = int(query.invoice_payload.split("_")[1])
    order = await db.get_order(order_id)
    if not order or order["status"] != "pending":
        return await query.answer(ok=False, error_message="Заказ устарел")
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message, db: Database, bot: Bot):
    order_id = int(message.successful_payment.invoice_payload.split("_")[1])
    order = await db.get_order(order_id)
    if order:
        await _fulfill_order(order_id, order, message.from_user.id, db, bot)

@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_crypto(call: CallbackQuery, db: Database):
    parts = call.data.split("_")
    product_id = int(parts[2])
    currency = parts[3].upper()
    if not config.CRYPTOBOT_ENABLED:
        return await call.answer("Криптооплата недоступна", show_alert=True)
    product = await db.get_product(product_id)
    if not product:
        return
    stock = await db.get_stock_count(product_id)
    if stock == 0:
        return await call.answer("❌ Товар закончился", show_alert=True)
    order_id = await db.create_order(
        call.from_user.id, product_id, 1,
        product["price"], currency, f"crypto_{currency.lower()}"
    )
    from payments.cryptobot import CryptoBotPayment
    crypto = CryptoBotPayment(config.CRYPTOBOT_TOKEN)
    invoice = await crypto.create_invoice(
        amount=product["price"],
        currency=currency,
        description=product["name"],
        payload=str(order_id)
    )
    if invoice:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=invoice["pay_url"])],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_crypto_{order_id}")]
        ])
        await call.message.edit_text(
            f"💰 Оплата {currency}\nСумма: <b>{invoice['amount']} {currency}</b>\n\nПосле оплаты нажмите «Проверить»",
            reply_markup=kb
        )
    else:
        await call.answer("Ошибка создания счёта", show_alert=True)

@router.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto(call: CallbackQuery, db: Database, bot: Bot):
    order_id = int(call.data.split("_")[2])
    order = await db.get_order(order_id)
    if not order or order["status"] != "pending":
        return await call.answer("Заказ уже обработан", show_alert=True)
    from payments.cryptobot import CryptoBotPayment
    crypto = CryptoBotPayment(config.CRYPTOBOT_TOKEN)
    paid = await crypto.check_invoice(str(order_id))
    if paid:
        await _fulfill_order(order_id, order, call.from_user.id, db, bot)
    else:
        await call.answer("⏳ Оплата ещё не поступила", show_alert=True)

@router.callback_query(F.data.startswith("pay_kassa_"))
async def pay_kassa(call: CallbackQuery, db: Database):
    parts = call.data.split("_")
    product_id = int(parts[2])
    currency = parts[3].upper()
    if not config.YOOKASSA_ENABLED:
        return await call.answer("Оплата картой недоступна", show_alert=True)
    product = await db.get_product(product_id)
    if not product:
        return
    order_id = await db.create_order(
        call.from_user.id, product_id, 1,
        product["price"], currency, f"kassa_{currency.lower()}"
    )
    from payments.yookassa import YooKassaPayment
    kassa = YooKassaPayment(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET)
    bot_info = await call.bot.get_me()
    payment = await kassa.create_payment(
        amount=product["price"],
        currency=currency,
        description=product["name"],
        order_id=order_id,
        return_url=f"https://t.me/{bot_info.username}"
    )
    if payment:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment["url"])],
            [InlineKeyboardButton(text="✅ Проверить", callback_data=f"check_kassa_{order_id}_{payment['id']}")]
        ])
        await call.message.edit_text(
            f"💳 Оплата картой\nСумма: <b>{product['price']} {currency}</b>\n\nПосле оплаты нажмите «Проверить»",
            reply_markup=kb
        )
    else:
        await call.answer("Ошибка создания платежа", show_alert=True)

@router.callback_query(F.data.startswith("check_kassa_"))
async def check_kassa(call: CallbackQuery, db: Database, bot: Bot):
    parts = call.data.split("_")
    order_id = int(parts[2])
    payment_id = parts[3]
    order = await db.get_order(order_id)
    if not order or order["status"] != "pending":
        return await call.answer("Заказ уже обработан", show_alert=True)
    from payments.yookassa import YooKassaPayment
    kassa = YooKassaPayment(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET)
    paid = await kassa.check_payment(payment_id)
    if paid:
        await _fulfill_order(order_id, order, call.from_user.id, db, bot)
    else:
        await call.answer("⏳ Оплата ещё не поступила", show_alert=True)

@router.callback_query(F.data.startswith("pay_steam_"))
async def pay_steam(call: CallbackQuery, db: Database):
    product_id = int(call.data.split("_")[2])
    product = await db.get_product(product_id)
    if not product or not config.STEAM_ENABLED:
        return await call.answer("Недоступно", show_alert=True)
    order_id = await db.create_order(
        call.from_user.id, product_id, 1,
        product["price"], "STEAM", "steam"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я отправил скины", callback_data=f"steam_sent_{order_id}")]
    ])
    await call.message.edit_text(
        f"🎮 Отправьте скины на сумму {product['price']} ₽\n\n"
        f"Ссылка: <code>{config.STEAM_TRADE_URL}</code>\n\n"
        f"После отправки нажмите кнопку ниже.",
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("steam_sent_"))
async def steam_sent(call: CallbackQuery, db: Database, bot: Bot):
    order_id = int(call.data.split("_")[2])
    for admin_id in config.ADMIN_IDS:
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_approve_{order_id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
                ]
            ])
            await bot.send_message(admin_id, f"🎮 Steam оплата!\nЗаказ #{order_id}\nПользователь: {call.from_user.id}", reply_markup=kb)
        except Exception:
            pass
    await call.message.edit_text("⏳ Ожидайте проверки скинов. Обычно до 30 минут.")

async def _fulfill_order(order_id, order, user_id, db: Database, bot: Bot):
    product = await db.get_product(order["product_id"])

    # Автозакупка через Lolzteam
    if config.LOLZ_ENABLED and product.get("supplier_code"):
        from supplier.lolz_buyer import LolzBuyer
        buyer = LolzBuyer(config.LOLZ_TOKEN)
        item = await buyer.buy(int(product["supplier_code"]))
        if item:
            await db.add_items(order["product_id"], [item])

    items = await db.pop_items(order["product_id"], order["quantity"])
    if not items:
        await db.update_order(order_id, status="no_stock")
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"⚠️ Заказ #{order_id} оплачен но товар закончился!")
            except Exception:
                pass
        await bot.send_message(user_id, "⚠️ Товар закончился. Обратитесь в поддержку.")
        return

    await db.complete_order(order_id)
    items_text = "\n".join(f"<code>{item}</code>" for item in items)
    await bot.send_message(
        user_id,
        f"✅ <b>Заказ #{order_id} выполнен!</b>\n\n"
        f"🛍 {product['name']}\n\n"
        f"📦 Ваши данные:\n{items_text}\n\n"
        f"Спасибо за покупку!"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 Продажа!\n#{order_id} | {product['name']}\n"
                f"{order['total_price']} {order['currency']}"
            )
        except Exception:
            pass
