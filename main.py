import json
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

# Ma'lumotlarni o'qish/yozish funksiyalari
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Haftaning kunlari uchun tugmalar
def days_keyboard():
    buttons = [
        [KeyboardButton(text="Dushanba"), KeyboardButton(text="Seshanba")],
        [KeyboardButton(text="Chorshanba"), KeyboardButton(text="Payshanba")],
        [KeyboardButton(text="Juma"), KeyboardButton(text="Shanba")],
        [KeyboardButton(text="Yakshanba"), KeyboardButton(text="Har kuni ✅")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Soat tanlash uchun tugmalar
def time_keyboard():
    buttons = [
        [KeyboardButton(text="08:00"), KeyboardButton(text="10:00")],
        [KeyboardButton(text="12:00"), KeyboardButton(text="14:00")],
        [KeyboardButton(text="16:00"), KeyboardButton(text="18:00")],
        [KeyboardButton(text="20:00"), KeyboardButton(text="22:00")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Sozlamalarni o'zgartirish menyusi
def settings_menu():
    buttons = [
        [KeyboardButton(text="✏️ Javob matnini o‘zgartirish")],
        [KeyboardButton(text="📅 Kunlarni o‘zgartirish")],
        [KeyboardButton(text="⏰ Vaqtni o‘zgartirish")],
        [KeyboardButton(text="✅ Hammasini ko‘rish")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# /start bosilganda
@dp.message(CommandStart())
async def start_cmd(msg: types.Message):
    user_id = str(msg.from_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {"step": "reply_text"}
        save_data(data)
        await msg.answer(
            "Salom 👋\nMen siz uchun avtomatik javob botiman.\n\n"
            "Avvalo, menga shaxsiy xabarlarga qanday javob yozishimni ayting (2000 belgigacha):"
        )
    else:
        await msg.answer("⚙️ Sozlamalar menyusi:", reply_markup=settings_menu())

# Foydalanuvchi javob matni kiritadi
@dp.message(F.text & (lambda m: len(m.text) <= 2000))
async def process_steps(msg: types.Message):
    user_id = str(msg.from_user.id)
    data = load_data()

    if user_id not in data:
        return

    user = data[user_id]

    # 1. Javob matni
    if user.get("step") == "reply_text":
        user["reply_text"] = msg.text
        user["step"] = "days"
        save_data(data)
        await msg.answer("📅 Qaysi kunlarda ishlasin?", reply_markup=days_keyboard())

    # 2. Kunlar tanlandi
    elif user.get("step") == "days":
        user["days"] = msg.text
        user["step"] = "start_time"
        save_data(data)
        await msg.answer("⏰ Boshlanish vaqtini tanlang:", reply_markup=time_keyboard())

    # 3. Boshlanish vaqti
    elif user.get("step") == "start_time":
        user["start_time"] = msg.text
        user["step"] = "end_time"
        save_data(data)
        await msg.answer("🏁 Tugash vaqtini tanlang:", reply_markup=time_keyboard())

    # 4. Tugash vaqti
    elif user.get("step") == "end_time":
        user["end_time"] = msg.text
        user["step"] = "done"
        save_data(data)
        await msg.answer(
            f"✅ Sozlamalar saqlandi!\n\n"
            f"📅 Kunlar: {user['days']}\n"
            f"⏰ {user['start_time']} — {user['end_time']}\n"
            f"💬 Javob: {user['reply_text']}",
            reply_markup=settings_menu(),
        )

    # Tahrirlash menyusidan kiritilgan so‘zlar
    elif msg.text == "✏️ Javob matnini o‘zgartirish":
        user["step"] = "reply_text"
        save_data(data)
        await msg.answer("📝 Yangi javob matnini yozing:")
    elif msg.text == "📅 Kunlarni o‘zgartirish":
        user["step"] = "days"
        save_data(data)
        await msg.answer("📅 Yangi kunlarni tanlang:", reply_markup=days_keyboard())
    elif msg.text == "⏰ Vaqtni o‘zgartirish":
        user["step"] = "start_time"
        save_data(data)
        await msg.answer("⏰ Yangi boshlanish vaqtini tanlang:", reply_markup=time_keyboard())
    elif msg.text == "✅ Hammasini ko‘rish":
        txt = (
            f"📅 Kunlar: {user.get('days', '-')}\n"
            f"⏰ {user.get('start_time', '-')} — {user.get('end_time', '-')}\n"
            f"💬 Javob: {user.get('reply_text', '-')}"
        )
        await msg.answer(txt)

    save_data(data)

# Kimdir yozsa, avtomatik javob
@dp.message()
async def auto_reply(msg: types.Message):
    sender_id = str(msg.chat.id)
    data = load_data()

    for user_id, info in data.items():
        if info.get("step") == "done":
            start = info.get("start_time", "00:00")
            end = info.get("end_time", "23:59")

            now = datetime.now().strftime("%H:%M")
            if start <= now <= end:
                await bot.send_message(sender_id, info["reply_text"])
                break

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
