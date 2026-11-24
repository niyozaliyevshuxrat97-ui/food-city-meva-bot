import os
import logging
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

PRODUCTS = {
    "apple": {"name": "Olma", "price": 15000, "unit": "kg", "category": "Mevalar"},
    "banana": {"name": "Banan", "price": 25000, "unit": "kg", "category": "Mevalar"},
    "orange": {"name": "Apelsin", "price": 22000, "unit": "kg", "category": "Mevalar"},
    "tomato": {"name": "Pomidor", "price": 18000, "unit": "kg", "category": "Sabzavotlar"},
    "potato": {"name": "Kartoshka", "price": 7000, "unit": "kg", "category": "Sabzavotlar"},
    "rice": {"name": "Guruch", "price": 18000, "unit": "kg", "category": "Oziq-ovqat"},
}
carts = defaultdict(dict)
states = {}

def money(value):
    return f"{value:,}".replace(",", " ") + " so'm"

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍎 Mevalar", callback_data="cat:Mevalar"),
         InlineKeyboardButton("🥬 Sabzavotlar", callback_data="cat:Sabzavotlar")],
        [InlineKeyboardButton("🛒 Oziq-ovqat", callback_data="cat:Oziq-ovqat")],
        [InlineKeyboardButton("🧺 Savatcham", callback_data="cart"),
         InlineKeyboardButton("📦 Buyurtma berish", callback_data="checkout")],
        [InlineKeyboardButton("ℹ️ Aloqa", callback_data="contact")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 🍏 FOOD CITY MEVA onlayn do'koniga xush kelibsiz.\n"
        "Mahsulot tanlash uchun bo'limni bosing:",
        reply_markup=main_menu()
    )

async def category(query, name):
    rows = []
    for key, item in PRODUCTS.items():
        if item["category"] == name:
            rows.append([InlineKeyboardButton(
                f'{item["name"]} — {money(item["price"])}/{item["unit"]}',
                callback_data=f"add:{key}"
            )])
    rows.append([InlineKeyboardButton("⬅️ Bosh menyu", callback_data="home")])
    await query.edit_message_text(
        f"{name}\nMahsulotni tanlang. Narxlar hozircha namunaviy.",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def show_cart(query, uid):
    cart = carts[uid]
    if not cart:
        await query.edit_message_text("Savatchangiz bo'sh.", reply_markup=main_menu())
        return
    lines, total = [], 0
    for key, qty in cart.items():
        item = PRODUCTS[key]
        subtotal = item["price"] * qty
        total += subtotal
        lines.append(f'{item["name"]}: {qty} {item["unit"]} — {money(subtotal)}')
    lines.append(f"\nJami: {money(total)}")
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Savatchani tozalash", callback_data="clear")],
        [InlineKeyboardButton("📦 Buyurtma berish", callback_data="checkout")],
        [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="home")]
    ]))

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid, data = q.from_user.id, q.data
    if data == "home":
        await q.edit_message_text("FOOD CITY MEVA — bo'limni tanlang:", reply_markup=main_menu())
    elif data.startswith("cat:"):
        await category(q, data.split(":", 1)[1])
    elif data.startswith("add:"):
        key = data.split(":", 1)[1]
        carts[uid][key] = carts[uid].get(key, 0) + 1
        await q.answer(f'{PRODUCTS[key]["name"]} savatga qo‘shildi')
    elif data == "cart":
        await show_cart(q, uid)
    elif data == "clear":
        carts[uid].clear()
        await q.edit_message_text("Savatcha tozalandi.", reply_markup=main_menu())
    elif data == "checkout":
        if not carts[uid]:
            await q.edit_message_text("Avval mahsulot tanlang.", reply_markup=main_menu())
        else:
            states[uid] = "name"
            await q.edit_message_text("Ism-familiyangizni yozing:")
    elif data == "contact":
        await q.edit_message_text("FOOD CITY MEVA\nTelefon raqami admin tomonidan kiritiladi.", reply_markup=main_menu())
    elif data.startswith("delivery:"):
        method = data.split(":", 1)[1]
        context.user_data["delivery"] = "Yetkazib berish" if method == "delivery" else "Do'kondan olib ketish"
        if method == "delivery":
            states[uid] = "address"
            await q.edit_message_text("Yetkazib berish manzilini yozing:")
        else:
            context.user_data["address"] = "Do'kondan olib ketish"
            states[uid] = "payment"
            await q.edit_message_text("To'lov turini tanlang:", reply_markup=payment_menu())
    elif data.startswith("pay:"):
        payment = data.split(":", 1)[1]
        lines, total = [], 0
        for key, qty in carts[uid].items():
            item = PRODUCTS[key]
            subtotal = item["price"] * qty
            total += subtotal
            lines.append(f'{item["name"]}: {qty} {item["unit"]} — {money(subtotal)}')
        msg = (
            "🆕 FOOD CITY MEVA — YANGI BUYURTMA\n\n" + "\n".join(lines) +
            f"\n\nJami: {money(total)}" +
            f'\nIsm: {context.user_data.get("name", "-")}' +
            f'\nTelefon: {context.user_data.get("phone", "-")}' +
            f'\nOlish usuli: {context.user_data.get("delivery", "-")}' +
            f'\nManzil: {context.user_data.get("address", "-")}' +
            f"\nTo'lov: {payment}\nTelegram ID: {uid}"
        )
        if ADMIN_ID:
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
            except Exception:
                log.exception("Admin xabarini yuborib bo'lmadi")
        carts[uid].clear()
        states.pop(uid, None)
        await q.edit_message_text(
            "✅ Buyurtmangiz qabul qilindi. Admin siz bilan bog'lanadi.\n"
            "Eslatma: Click/Payme hozircha to'lov usulini tanlash xolos; avtomatik to'lov ulanmagan.",
            reply_markup=main_menu()
        )

def payment_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 Naqd pul", callback_data="pay:Naqd pul")],
        [InlineKeyboardButton("💳 Karta", callback_data="pay:Karta")],
        [InlineKeyboardButton("📲 Click", callback_data="pay:Click")],
        [InlineKeyboardButton("📲 Payme", callback_data="pay:Payme")]
    ])

async def text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = states.get(uid)
    if state == "name":
        context.user_data["name"] = update.message.text.strip()
        states[uid] = "phone"
        await update.message.reply_text("Telefon raqamingizni yozing:")
    elif state == "phone":
        context.user_data["phone"] = update.message.text.strip()
        states[uid] = "delivery"
        await update.message.reply_text("Buyurtmani qanday olasiz?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚚 Yetkazib berish", callback_data="delivery:delivery")],
            [InlineKeyboardButton("🏬 Do'kondan olib ketish", callback_data="delivery:pickup")]
        ]))
    elif state == "address":
        context.user_data["address"] = update.message.text.strip()
        states[uid] = "payment"
        await update.message.reply_text("To'lov turini tanlang:", reply_markup=payment_menu())
    else:
        await update.message.reply_text("Menyudan foydalaning:", reply_markup=main_menu())

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Admin xizmati faol. Narxlarni hozircha bot.py ichidagi PRODUCTS ro'yxatidan o'zgartirish kerak.")
    else:
        await update.message.reply_text("Admin ruxsati yo'q.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_messages))

    from http.server import HTTPServer, BaseHTTPRequestHandler
    from threading import Thread

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"FOOD CITY MEVA BOT ishlayapti")

        def log_message(self, *args):
            pass

    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()

    app.run_polling()


if __name__ == "__main__":
    main()
