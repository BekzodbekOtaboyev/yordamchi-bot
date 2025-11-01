import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from aiohttp import web
from dotenv import load_dotenv

# --- Muhit o‘zgaruvchilarni yuklash ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Ma'lumotlar fayli ---
DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

# --- Holatlar ---
class Form(StatesGroup):
    message = State()
    audience = State()
    mode = State()
    days = State()
    start_time = State()
    end_time = State()
    manual_start = State()
    manual_end = State()

# --- Tugmalar ---
def days_keyboard():
    kb = [
        [KeyboardButton(text="Dushanba"), KeyboardButton(text="Seshanba")],
        [KeyboardButton(text="Chorshanba"), KeyboardButton(text="Payshanba")],
        [KeyboardButton(text="Juma"), KeyboardButton(text="Shanba")],
        [KeyboardButton(text="Yakshanba"), KeyboardButton(text="Har kuni ✅")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def time_keyboard():
    rows = []
    hours = [f"{str(h).zfill(2)}:00" for h in range(1, 24)]
    for i in range(0, len(hours), 3):
        rows.append([KeyboardButton(text=t) for t in hours[i:i+3]])
    rows.append([KeyboardButton(text="Qo‘lda kiritish")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def edit_keyboard():
    kb = [
        [KeyboardButton(text="📝 Xabarni o‘zgartirish")],
        [KeyboardButton(text="🕐 Vaqtni o‘zgartirish")],
        [KeyboardButton(text="📅 Kunlarni o‘zgartirish")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- /start komandasi ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    user_id = str(message.from_user.id)

    if user_id in data:
        info = data[user_id]
        await message.answer(
            f"✅ Sizda avvaldan sozlamalar mavjud:\n\n"
            f"📨 Xabar: {info['message']}\n"
            f"🎯 Kimlarga: {info['audience']}\n"
            f"⚙️ Rejim: {info['mode']}\n"
            f"📅 Kun: {info['days']}\n"
            f"🕓 Vaqt: {info['start_time']} - {info['end_time']}\n\n"
            "Quyidagilardan birini tanlang 👇",
            reply_markup=edit_keyboard()
        )
    else:
        await message.answer(
            "👋 Salom!\nMen sizga yozgan birinchi foydalanuvchilarga avtomatik javob yuboruvchi botman.\n\n"
            "Avvalo, yuboriladigan xabaringizni yozing:"
        )
        await state.set_state(Form.message)

# --- Ma’lumot yig‘ish bosqichlari ---
@dp.message(Form.message)
async def get_message(message: types.Message, state: FSMContext):
    await state.update_data(message_text=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Faqat yangi yozganlarga")],
            [KeyboardButton(text="Barchaga (eski + yangi)")]
        ],
        resize_keyboard=True
    )
    await message.answer("Xabar kimlarga yuborilsin?", reply_markup=kb)
    await state.set_state(Form.audience)

@dp.message(Form.audience)
async def get_audience(message: types.Message, state: FSMContext):
    await state.update_data(audience=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Faqat online paytimda")],
            [KeyboardButton(text="Har doim ishlasin ✅")]
        ],
        resize_keyboard=True
    )
    await message.answer("Bot qachon ishlasin?", reply_markup=kb)
    await state.set_state(Form.mode)

@dp.message(Form.mode)
async def get_mode(message: types.Message, state: FSMContext):
    await state.update_data(mode=message.text)
    await message.answer("🗓 Haftalik kunlardan birini tanlang:", reply_markup=days_keyboard())
    await state.set_state(Form.days)

@dp.message(Form.days)
async def get_days(message: types.Message, state: FSMContext):
    await state.update_data(days=message.text)
    await message.answer("🕐 Boshlanish vaqtini tanlang:", reply_markup=time_keyboard())
    await state.set_state(Form.start_time)

@dp.message(Form.start_time)
async def get_start_time(message: types.Message, state: FSMContext):
    if message.text == "Qo‘lda kiritish":
        await message.answer("⏰ Masalan: 09:00")
        await state.set_state(Form.manual_start)
    else:
        await state.update_data(start_time=message.text)
        await message.answer("⏰ Tugash vaqtini tanlang:", reply_markup=time_keyboard())
        await state.set_state(Form.end_time)

@dp.message(Form.manual_start)
async def manual_start(message: types.Message, state: FSMContext):
    await state.update_data(start_time=message.text)
    await message.answer("⏰ Tugash vaqtini tanlang:", reply_markup=time_keyboard())
    await state.set_state(Form.end_time)

@dp.message(Form.end_time)
async def get_end_time(message: types.Message, state: FSMContext):
    if message.text == "Qo‘lda kiritish":
        await message.answer("⏰ Masalan: 18:00")
        await state.set_state(Form.manual_end)
    else:
        await finalize_user_data(message, state)

@dp.message(Form.manual_end)
async def manual_end(message: types.Message, state: FSMContext):
    await finalize_user_data(message, state)

async def finalize_user_data(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = str(message.from_user.id)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    db[user_id] = {
        "message": data["message_text"],
        "audience": data["audience"],
        "mode": data["mode"],
        "days": data["days"],
        "start_time": data["start_time"],
        "end_time": message.text,
        "sent_users": []
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    await message.answer("✅ Sozlamalar saqlandi!", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

# --- Sozlamalarni tahrirlash ---
@dp.message(lambda m: m.text in ["📝 Xabarni o‘zgartirish", "🕐 Vaqtni o‘zgartirish", "📅 Kunlarni o‘zgartirish"])
async def edit_settings(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if user_id not in data:
        await message.answer("⚙️ Avval /start orqali sozlamalarni yarating.")
        return

    if message.text == "📝 Xabarni o‘zgartirish":
        await message.answer("Yangi avtomatik xabarni yuboring:")
        await state.set_state(Form.message)
    elif message.text == "🕐 Vaqtni o‘zgartirish":
        await message.answer("🕐 Boshlanish vaqtini kiriting:", reply_markup=time_keyboard())
        await state.set_state(Form.start_time)
    elif message.text == "📅 Kunlarni o‘zgartirish":
        await message.answer("📅 Haftalik kunni tanlang:", reply_markup=days_keyboard())
        await state.set_state(Form.days)

# --- Avtomatik javob berish ---
@dp.message()
async def auto_reply(message: types.Message):
    user_id = str(message.from_user.id)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Agar sozlamalar bo'lmasa — chiqib ketadi
    if user_id not in data:
        return

    info = data[user_id]
    reply_text = info["message"]
    sent_users = info.get("sent_users", [])

    target_id = str(message.from_user.id)
    if target_id not in sent_users:
        await bot.send_message(chat_id=target_id, text=reply_text)
        sent_users.append(target_id)
        info["sent_users"] = sent_users
        data[user_id] = info

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# --- Webhook funksiyalari ---
async def on_startup():
    webhook_url = f"{RENDER_URL}/webhook"
    await bot.set_webhook(webhook_url)
    print("✅ Webhook o‘rnatildi:", webhook_url)

async def handle_webhook(request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response()

app = web.Application()
app.router.add_post("/webhook", handle_webhook)

async def main():
    await on_startup()
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print("🤖 Bot ishga tushdi!")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
