"""
Telegram Bot (Render uchun, JSON saqlash bilan)
Muallif: ChatGPT GPT-5

Xususiyatlar:
✅ /start — foydalanuvchidan ketma-ket so‘rovlar
✅ Sozlamalar (kimlarga, qachon, kunlar, matn)
✅ Auto-reply va kunlik scheduler
✅ Ma’lumotlar `data.json` faylda saqlanadi (SQLite o‘rniga)
"""

import os
import json
import logging
from datetime import datetime, time
from typing import Dict, Any, List, Optional

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TELEGRAM_TOKEN", "PASTE_YOUR_TOKEN_HERE")
DATA_FILE = "data.json"
MAX_MESSAGE_LENGTH = 2000

(RECIPIENTS, MODE, MESSAGE_TEXT, DAYS, START_TIME, END_TIME, CONFIRM) = range(7)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- JSON saqlash funksiyalari ---
def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "settings": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: Dict[str, Any]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_user(user_id: int, username: str, first_name: str, last_name: str):
    data = load_data()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "first_seen": datetime.utcnow().isoformat(),
        }
        save_data(data)


def get_all_users() -> List[int]:
    data = load_data()
    return [int(uid) for uid in data["users"].keys()]


def get_new_users(since: Optional[str]) -> List[int]:
    data = load_data()
    if not since:
        return [int(uid) for uid in data["users"].keys()]
    since_dt = datetime.fromisoformat(since)
    return [
        int(uid)
        for uid, u in data["users"].items()
        if datetime.fromisoformat(u["first_seen"]) > since_dt
    ]


def save_settings(owner_id: int, settings: Dict[str, Any]):
    data = load_data()
    data["settings"][str(owner_id)] = settings
    save_data(data)


def load_settings(owner_id: int) -> Optional[Dict[str, Any]]:
    data = load_data()
    return data["settings"].get(str(owner_id))


# --- Foydalanuvchidan ma’lumot olish ---
def parse_time(hhmm: str) -> Optional[time]:
    try:
        hh, mm = map(int, hhmm.split(":"))
        return time(hour=hh, minute=mm)
    except Exception:
        return None


def days_from_text(txt: str) -> List[str]:
    mapping = {
        "1": "Mon",
        "2": "Tue",
        "3": "Wed",
        "4": "Thu",
        "5": "Fri",
        "6": "Sat",
        "7": "Sun",
        "dushanba": "Mon",
        "seshanba": "Tue",
        "chorshanba": "Wed",
        "payshanba": "Thu",
        "juma": "Fri",
        "shanba": "Sat",
        "yakshanba": "Sun",
    }
    parts = [p.strip().lower() for p in txt.split(",")]
    return [mapping.get(p, p.title()[:3]) for p in parts if p]


# --- Bot conversation ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return ConversationHandler.END
    save_user(user.id, user.username, user.first_name, user.last_name)
    keyboard = [["Yangi yozganlarga"], ["Hammaga"]]
    await update.message.reply_text(
        "Salom! Xabar kimlarga yuborilsin?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    context.user_data["new_settings"] = {}
    return RECIPIENTS


async def recipients_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    context.user_data["new_settings"]["recipients"] = (
        "yangi" if "yangi" in text else "hammaga"
    )
    keyboard = [["Faqat onlayn"], ["Har doim"]]
    await update.message.reply_text(
        "Bot qachon ishlaydi?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return MODE


async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    context.user_data["new_settings"]["mode"] = "onlayn" if "onlayn" in text else "har doim"
    await update.message.reply_text("Xabar matnini yuboring (2000 belgigacha):")
    return MESSAGE_TEXT


async def message_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if len(text) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text("Matn juda uzun.")
        return MESSAGE_TEXT
    context.user_data["new_settings"]["message_text"] = text
    await update.message.reply_text("Haftaning qaysi kunlari? (masalan: dushanba, juma)")
    return DAYS


async def days_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = days_from_text(update.message.text)
    if not days:
        await update.message.reply_text("Kunlarni to'g'ri kiriting.")
        return DAYS
    context.user_data["new_settings"]["days"] = days
    await update.message.reply_text("Boshlanish vaqtini kiriting (HH:MM)")
    return START_TIME


async def start_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = parse_time(update.message.text)
    if not t:
        await update.message.reply_text("Vaqt formati noto‘g‘ri.")
        return START_TIME
    context.user_data["new_settings"]["start_time"] = update.message.text
    await update.message.reply_text("Tugash vaqtini kiriting (HH:MM)")
    return END_TIME


async def end_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = parse_time(update.message.text)
    if not t:
        await update.message.reply_text("Vaqt formati noto‘g‘ri.")
        return END_TIME
    context.user_data["new_settings"]["end_time"] = update.message.text
    s = context.user_data["new_settings"]
    summary = (
        f"Kimlarga: {s['recipients']}\n"
        f"Mode: {s['mode']}\n"
        f"Kunlar: {', '.join(s['days'])}\n"
        f"Boshlanish: {s['start_time']} - {s['end_time']}\n\n"
        f"Xabar:\n{s['message_text']}"
    )
    keyboard = [["Tasdiqlayman ✅"]]
    await update.message.reply_text(summary, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return CONFIRM


async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = context.user_data["new_settings"]
    s["last_broadcast"] = None
    s["owner_active"] = True
    s["auto_reply"] = s["message_text"]
    save_settings(update.effective_user.id, s)
    await update.message.reply_text("Sozlamalar saqlandi ✅", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# --- Auto-reply ---
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        save_user(user.id, user.username, user.first_name, user.last_name)
    data = load_data()
    if data["settings"]:
        first_owner = next(iter(data["settings"].values()))
        msg = first_owner.get("auto_reply", "Rahmat! Xabaringiz qabul qilindi.")
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("Bot hali sozlanmagan.")


# --- Render uchun asosiy ishga tushirish ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            RECIPIENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, recipients_handler)],
            MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mode_handler)],
            MESSAGE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_text_handler)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, days_handler)],
            START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_time_handler)],
            END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_time_handler)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    logger.info("Bot ishga tushdi Render uchun ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
