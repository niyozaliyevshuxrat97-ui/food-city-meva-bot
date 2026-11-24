import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["TELEGRAM_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

PRODUCTS = {
    "apple": ("Olma", 15000, "kg", "Mevalar"),
    "banana": ("Banan", 25000, "kg", "Mevalar"),
    "orange": ("Apelsin", 22000, "kg", "Mevalar"),
    "tomato": ("Pomidor", 18000, "kg", "Sabzavotlar"),
    "potato": ("Kartoshka", 7000, "kg", "Sabzavotlar"),
    "rice": ("Guruch", 18000, "kg", "Oziq-ovqat"),
}
CART = {}
STATE = {}

def money(n):
    return f"{n:,}".replace(",", " ") + " so'm"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍎 Mevalar", callback_data="cat:Mevalar"),
         InlineKeyboardButton("🥬 Sabzavotlar", callback_data="cat:Sabzavotlar")],
        [InlineKeyboardButton("🛒 Oziq-ovqat", callback_data="cat:Oziq-ovqat")],
        [InlineKeyboardButton("🧺 Savatcham", callback_data="cart")],
        [InlineKeyboardButton("📦 Buyurtma berish", callback_data="checkout")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    CART.setdefault(update.effective_user.id, {})
    await update.message.reply_text("Assalomu alaykum! 🍏 FOOD CITY MEVA do'koniga xush kelibsiz.", reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid, data = q.from_user.id, q.data
    CART.setdefault(uid, {})
    if data.startswith("cat:"):
        cat = data.split(":", 1)[1]
        rows = [[InlineKeyboardButton(f"{v[0]} — {money(v[1])}/{v[2]}", callback_data=f"add:{k}")]
                for k, v in PRODUCTS.items() if v[3] == cat]
        rows.append([InlineKeyboardButton("⬅️ Menyu", callback_data="home")])
        await q.edit_message_text(f"{cat} — mahsulotni tanlang:", reply_markup=InlineKeyboardMarkup(rows))
    elif data.startswith("add:"):
        key = data.split(":", 1)[1]
        CART[uid][key] = CART[uid].get(key, 0) + 1
        await q.answer("Savatchaga qo'shildi")
    elif data == "home":
        await q.edit_message_text("Bo'limni tanlang:", reply_markup=menu())
    elif data == "cart":
        lines, total = [], 0
        for key, qty in CART[uid].items():
            name, price, unit, _ = PRODUCTS[key]
            total += price * qty
            lines.append(f"{name}: {qty} {unit} — {money(price * qty)}")
        await q.edit_message_text("\n".join(lines) + (f"\nJami: {money(total)}" if lines else "Savatcha bo'sh."), reply_markup=menu())
    elif data == "checkout":
        if not CART[uid]:
            await q.edit_message_text("Avval mahsulot tanlang.", reply_markup=menu())
        else:
            STATE[uid] = "name"
            await q.edit_message_text("Ism-familiyangizni yozing:")

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = STATE.get(uid)
    if state == "name":
        context.user_data["name"] = update.message.text
        STATE[uid] = "phone"
        await update.message.reply_text("Telefon raqamingizni yozing:")
    elif state == "phone":
        context.user_data["phone"] = update.message.text
        STATE[uid] = "delivery"
        await update.message.reply_text("Olish usuli: yetkazib berish yoki do'kondan olib ketish deb yozing:")
    elif state == "delivery":
        context.user_data["delivery"] = update.message.text
        STATE[uid] = "address"
        await update.message.reply_text("Manzilni yozing (olib ketish bo'lsa '-' yozing):")
    elif state == "address":
        context.user_data["address"] = update.message.text
        STATE[uid] = "payment"
        await update.message.reply_text("To'lov turini yozing: Naqd pul / Karta / Click / Payme")
    elif state == "payment":
        context.user_data["payment"] = update.message.text
        lines, total = [], 0
        for key, qty in CART.get(uid, {}).items():
            name, price, unit, _ = PRODUCTS[key]
            lines.append(f"{name}: {qty} {unit} — {money(price * qty)}")
            total += price * qty
        msg = ("🆕 FOOD CITY MEVA BUYURTMASI\n" + "\n".join(lines) +
               f"\nJami: {money(total)}\nIsm: {context.user_data.get('name')}\n"
               f"Telefon: {context.user_data.get('phone')}\nOlish: {context.user_data.get('delivery')}\n"
               f"Manzil: {context.user_data.get('address')}\nTo'lov: {context.user_data.get('payment')}\n"
               f"Telegram ID: {uid}")
        if ADMIN_ID:
            await context.bot.send_message(ADMIN_ID, msg)
        CART[uid] = {}
        STATE.pop(uid, None)
        await update.message.reply_text("Buyurtmangiz qabul qilindi! Admin siz bilan bog'lanadi.", reply_markup=menu())
    else:
        await update.message.reply_text("Menyudan boshlash uchun /start bosing.", reply_markup=menu())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    app.run_polling()

if __name__ == "__main__":
    main()
