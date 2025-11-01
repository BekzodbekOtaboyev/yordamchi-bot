import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from aiohttp import web
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

# --- Haftalik tugmalar ---
def days_keyboard():
    kb = [
        [KeyboardButton(text="Dushanba"), KeyboardButton(text="Seshanba")],
        [KeyboardButton(text="Chorshanba"), KeyboardButton(text="Payshanba")],
        [KeyboardButton(text="Juma"), KeyboardButton(text="Shanba")],
        [KeyboardButton(text="Yakshanba"), KeyboardButton(text="Har kuni ✅")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- Soat tugmalari ---
def time_keyboard():
    rows = []
    hours = [f"{str(h).zfill(2)}:00" for h in range(1, 24)]
    for i in range(0, len(hours), 3):
        rows.append([KeyboardButton(text=t) for t in hours[i:i+3]])
    rows.append([KeyboardButton(text="Qo‘lda kiritish")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await message.answer(
        "👋 Salom!\n\n"
        "Men chatlarga qanday habar yuborishim kerak?\n"
        "✉️ Xabar sizga birinchi yozgan (tanishish maqsadidagi) chat egasiga yuboriladi.\n"
        "(maksimum 2000 belgi)\n\n"
        "Iltimos, o‘zingizning maxsus xabaringizni yozing:"
    )
    await state.set_state(Form.message)

@dp.message(Form.message)
async def get_message(message: types.Message, state: FSMContext):
    await state.update_data(message_text=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Faqat yangi yozganlarga")],
            [KeyboardButton(text="Barchaga (eski, yangi, kontaktlar)")]
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
    await message.answer("Bot faqat online paytingizda ishlasinmi yoki har doim?", reply_markup=kb)
    await state.set_state(Form.mode)

@dp.message(Form.mode)
async def get_mode(message: types.Message, state: FSMContext):
    await state.update_data(mode=message.text)
    await message.answer("🗓 Endi hafta kunlarini tanlang:", reply_markup=days_keyboard())
    await state.set_state(Form.days)

@dp.message(Form.days)
async def get_days(message: types.Message, state: FSMContext):
    await state.update_data(days=message.text)
    await message.answer("🕐 Xabar yuborish boshlanish vaqtini tanlang:", reply_markup=time_keyboard())
    await state.set_state(Form.start_time)

@dp.message(Form.start_time)
async def get_start_time(message: types.Message, state: FSMContext):
    if message.text == "Qo‘lda kiritish":
        await message.answer("⏰ Boshlanish vaqtini qo‘lda kiriting (masalan: 09:00):")
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
        await message.answer("⏰ Tugash vaqtini qo‘lda kiriting (masalan: 18:00):")
        await state.set_state(Form.manual_end)
    else:
        await state.update_data(end_time=message.text)
        data = await state.get_data()
        await message.answer(
            "✅ Ma’lumotlar saqlandi!\n\n"
            f"📨 Xabar: {data['message_text']}\n"
            f"🎯 Kimlarga: {data['audience']}\n"
            f"⚙️ Rejim: {data['mode']}\n"
            f"📅 Kunlar: {data['days']}\n"
            f"🕓 Vaqt: {data['start_time']} dan {data['end_time']} gacha\n\n"
            "Endi bot tayyor!"
        )
        await state.clear()

@dp.message(Form.manual_end)
async def manual_end(message: types.Message, state: FSMContext):
    await state.update_data(end_time=message.text)
    data = await state.get_data()
    await message.answer(
        "✅ Ma’lumotlar saqlandi!\n\n"
        f"📨 Xabar: {data['message_text']}\n"
        f"🎯 Kimlarga: {data['audience']}\n"
        f"⚙️ Rejim: {data['mode']}\n"
        f"📅 Kunlar: {data['days']}\n"
        f"🕓 Vaqt: {data['start_time']} dan {data['end_time']} gacha\n\n"
        "Endi bot tayyor!"
    )
    await state.clear()

# --- Webhook setup ---
async def on_startup():
    webhook_url = f"{RENDER_URL}/webhook"
    await bot.set_webhook(webhook_url)
    print("Webhook o‘rnatildi:", webhook_url)

async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()

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
    print("Bot ishga tushdi 🔥")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
