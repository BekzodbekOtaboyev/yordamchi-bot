import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

# 🧩 Ma'lumotlarni o'qish/yozish
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# 🟢 /start bosilganda
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    data = load_data()
    user_id = str(msg.from_user.id)
    if user_id not in data:
        data[user_id] = {}
        save_data(data)
    await msg.answer(
        "👋 Assalomu alaykum!\n\n"
        "Men sizning avtomatik yordamchingizman.\n"
        "Kimdir sizga birinchi marta yozsa — siz tanlagan xabarni yuboraman.\n\n"
        "Iltimos, yuboriladigan xabaringizni yozing ✍️ (maks. 2000 belgi):"
    )
    data[user_id]["step"] = "waiting_for_message"
    save_data(data)

# 🔹 Foydalanuvchi o'z xabarini yozganda
@dp.message()
async def get_user_message(msg: types.Message):
    data = load_data()
    user_id = str(msg.from_user.id)

    if user_id not in data:
        return await msg.answer("Iltimos, /start buyrug‘ini yuboring.")

    step = data[user_id].get("step")

    # 1️⃣ Foydalanuvchi xabarini yozadi
    if step == "waiting_for_message":
        data[user_id]["auto_message"] = msg.text[:2000]
        data[user_id]["step"] = "choose_days"
        save_data(data)

        # Haftaning kunlari tugmalari
        kb = InlineKeyboardBuilder()
        days = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba", "Har kuni"]
        for d in days:
            kb.button(text=d, callback_data=f"day_{d}")
        kb.adjust(2)

        await msg.answer("📅 Qaysi kunlarda bu xabar yuborilsin?", reply_markup=kb.as_markup())

# 2️⃣ Kunlarni tanlash
@dp.callback_query(F.data.startswith("day_"))
async def choose_days(callback: types.CallbackQuery):
    data = load_data()
    user_id = str(callback.from_user.id)
    day = callback.data.replace("day_", "")
    data[user_id]["days"] = day
    data[user_id]["step"] = "choose_time"
    save_data(data)

    # Soat oralig'i tugmalari
    kb = InlineKeyboardBuilder()
    times = ["00-08", "08-12", "12-18", "18-23"]
    for t in times:
        kb.button(text=f"{t}:00", callback_data=f"time_{t}")
    kb.adjust(2)
    await callback.message.edit_text("⏰ Qaysi vaqt oralig‘ida xabar yuborilsin?", reply_markup=kb.as_markup())

# 3️⃣ Vaqt oralig‘ini tanlash
@dp.callback_query(F.data.startswith("time_"))
async def choose_time(callback: types.CallbackQuery):
    data = load_data()
    user_id = str(callback.from_user.id)
    t = callback.data.replace("time_", "")
    data[user_id]["time_range"] = t
    data[user_id]["step"] = "completed"
    save_data(data)

    await callback.message.edit_text(
        "✅ Sozlamalar saqlandi!\n\n"
        "Endi kimdir sizga yozsa, tanlagan kun va vaqtda sizning avtomatik xabaringiz yuboriladi.\n\n"
        "💡 Istasangiz /start buyrug‘i orqali xabarni o‘zgartirishingiz mumkin."
    )

# 💬 Kimdir foydalanuvchiga yozganda
@dp.message(F.chat.type == "private")
async def auto_reply(msg: types.Message):
    data = load_data()
    # Bu misolda — faqat test uchun avtomatik xabar yuborish
    for user_id, info in data.items():
        if info.get("step") == "completed":
            auto_msg = info.get("auto_message")
            time_range = info.get("time_range", "")
            days = info.get("days", "")

            now = datetime.now()
            day_name = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"][now.weekday()]
            hour = now.hour

            start, end = map(int, time_range.split("-"))

            # Agar tanlangan kun va vaqt to‘g‘ri bo‘lsa — xabar yuboriladi
            if (days == "Har kuni" or day_name == days) and (start <= hour <= end):
                await msg.answer(auto_msg)
                break

# 🔁 Ishga tushirish
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
