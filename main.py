import os
import json
import logging
from datetime import datetime, time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
from dotenv import load_dotenv
import asyncio

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

DB_FILE = "db.json"

# --- FSM holatlar ---
class Form(StatesGroup):
    message = State()
    audience = State()
    online_mode = State()
    weekday = State()
    start_hour = State()
    end_hour = State()

# --- bazani yuklash va saqlash ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": [], "messages": []}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# --- /start ---
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.message)
    await message.answer("Salom! 👋\nIltimos, yubormoqchi bo‘lgan xabaringizni yozing (2000 belgigacha):")

# --- xabar yozish ---
@dp.message(Form.message)
async def get_message(message: types.Message, state: FSMContext):
    if len(message.text) > 2000:
        return await message.answer("Xabaringiz juda uzun! Maksimum 2000 belgi.")
    await state.update_data(message=message.text)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Faqat yangi yozganlarga", callback_data="new")],
        [InlineKeyboardButton("❇️ Barchaga", callback_data="all")]
    ])
    await message.answer("Kimlarga yuborilsin?", reply_markup=keyboard)
    await state.set_state(Form.audience)

# --- kimlarga yuborish ---
@dp.callback_query(Form.audience)
async def choose_audience(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(audience=call.data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🟢 Faqat online paytimda", callback_data="online")],
        [InlineKeyboardButton("🔵 24 soat (doimiy)", callback_data="always")]
    ])
    await call.message.edit_text("Bot faqat online paytingizda ishlasinmi yoki doimiy bo‘lsin?", reply_markup=keyboard)
    await state.set_state(Form.online_mode)

# --- online/doimiy ---
@dp.callback_query(Form.online_mode)
async def choose_mode(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(online_mode=call.data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(1,8)],
        [InlineKeyboardButton("📅 Har kuni", callback_data="everyday")]
    ])
    await call.message.edit_text("Hafta kunlarini tanlang:", reply_markup=keyboard)
    await state.set_state(Form.weekday)

# --- hafta kunlari ---
@dp.callback_query(Form.weekday)
async def choose_weekday(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(weekday=call.data)

    # Soat boshlanishi
    hours_keyboard = [[InlineKeyboardButton(f"{h:02d}:00", callback_data=f"{h:02d}")] for h in range(0,24)]
    hours_keyboard.append([InlineKeyboardButton("⌨️ Qo‘lda kiritish", callback_data="manual_start")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=hours_keyboard)
    await call.message.edit_text("Xabar yuborishni boshlash soatini tanlang:", reply_markup=keyboard)
    await state.set_state(Form.start_hour)

# --- boshlanish soati ---
@dp.callback_query(Form.start_hour)
async def start_hour_cb(call: types.CallbackQuery, state: FSMContext):
    if call.data == "manual_start":
        await call.message.edit_text("Iltimos, boshlanish vaqtini (HH:MM) kiriting:")
        return
    await state.update_data(start_hour=call.data)
    await ask_end_hour(call.message, state)

@dp.message(Form.start_hour)
async def start_hour_manual(message: types.Message, state: FSMContext):
    await state.update_data(start_hour=message.text)
    await ask_end_hour(message, state)

# --- tugash soati ---
async def ask_end_hour(message, state: FSMContext):
    hours_keyboard = [[InlineKeyboardButton(f"{h:02d}:00", callback_data=f"{h:02d}")] for h in range(0,24)]
    hours_keyboard.append([InlineKeyboardButton("⌨️ Qo‘lda kiritish", callback_data="manual_end")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=hours_keyboard)
    await message.answer("Xabar yuborishni tugash soatini tanlang:", reply_markup=keyboard)
    await state.set_state(Form.end_hour)

@dp.callback_query(Form.end_hour)
async def end_hour_cb(call: types.CallbackQuery, state: FSMContext):
    if call.data == "manual_end":
        await call.message.edit_text("Iltimos, tugash vaqtini (HH:MM) kiriting:")
        return
    await state.update_data(end_hour=call.data)
    await save_all(call.message, state)

@dp.message(Form.end_hour)
async def end_hour_manual(message: types.Message, state: FSMContext):
    await state.update_data(end_hour=message.text)
    await save_all(message, state)

# --- saqlash va yakun ---
async def save_all(message, state):
    data = await state.get_data()
    db = load_db()

    # foydalanuvchi saqlash
    if message.from_user.id not in db["users"]:
        db["users"].append({"user_id": message.from_user.id, "sent_messages":[]})

    # xabar saqlash
    msg_id = len(db["messages"]) + 1
    db["messages"].append({
        "id": msg_id,
        "user_id": message.from_user.id,
        "message": data['message'],
        "audience": data['audience'],
        "online_mode": data['online_mode'],
        "weekday": data['weekday'],
        "start_hour": data['start_hour'],
        "end_hour": data['end_hour']
    })
    save_db(db)

    await message.answer("✅ Ma’lumotlar saqlandi, rahmat!")
    await state.clear()

# --- admin yuborish ---
async def send_messages():
    while True:
        db = load_db()
        now = datetime.now()
        weekday = now.isoweekday()  # 1-7
        current_hour = now.hour

        for msg in db["messages"]:
            # Doimiy xabar (24 soat) yoki kun va vaqtga mos
            send_flag = False
            if msg["online_mode"] == "always":
                send_flag = True
            else:
                # Hafta kuni tekshirish
                if msg["weekday"] == "everyday" or int(msg["weekday"]) == weekday:
                    start = int(msg["start_hour"].split(":")[0]) if ":" in msg["start_hour"] else int(msg["start_hour"])
                    end = int(msg["end_hour"].split(":")[0]) if ":" in msg["end_hour"] else int(msg["end_hour"])
                    if start <= current_hour <= end:
                        send_flag = True

            if send_flag:
                # userni topish
                user_record = next((u for u in db["users"] if u["user_id"]==msg["user_id"]), None)
                if user_record and msg["id"] not in user_record["sent_messages"]:
                    try:
                        await bot.send_message(msg["user_id"], msg["message"])
                        user_record["sent_messages"].append(msg["id"])
                        save_db(db)
                    except Exception as e:
                        print(f"Xabar yuborilmadi {msg['user_id']}: {e}")
        await asyncio.sleep(60)  # har 1 daqiqa tekshirish

# --- webhook ---
async def on_startup(app):
    asyncio.create_task(send_messages())
    webhook_url = "https://YOUR-RENDER-APP.onrender.com/webhook"
    await bot.set_webhook(webhook_url)

async def on_shutdown(app):
    await bot.delete_webhook()

async def handle_webhook(request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response()

def main():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    main()
