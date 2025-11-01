import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8448499638:AAFFqtNvsU285I_dfvWCv_XpFxA_PSVxZr8" 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# --- Holatlar (FSM) ---
class UserForm(StatesGroup):
    waiting_for_message = State()
    waiting_for_days = State()
    waiting_for_time = State()


# --- /start buyrug‘i ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Salom!\n\n"
        "Men chatlarga qanday xabar yuborishim kerak?\n"
        "✉️ Xabar sizga birinchi yozgan (tanishish maqsadidagi) chat egasiga yuboriladi.\n"
        "(maksimum 2000 belgi)\n\n"
        "Iltimos, o‘zingizning maxsus xabaringizni yozing:"
    )
    await state.set_state(UserForm.waiting_for_message)


# --- 1-bosqich: foydalanuvchi xabar yozadi ---
@dp.message(UserForm.waiting_for_message)
async def get_message(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text) > 2000:
        await message.answer("❗ Xabaringiz juda uzun, 2000 belgidan oshmasin.")
        return

    await state.update_data(user_message=text)

    # hafta kunlari tugmalari
    days_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Dushanba"), KeyboardButton(text="Seshanba")],
            [KeyboardButton(text="Chorshanba"), KeyboardButton(text="Payshanba")],
            [KeyboardButton(text="Juma"), KeyboardButton(text="Shanba")],
            [KeyboardButton(text="Yakshanba")],
            [KeyboardButton(text="Har kuni ✅")],
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📅 Endi, haftaning qaysi kunlarida xabar yuborilsin?\n"
        "Bir yoki bir nechta kunni tanlang, so‘ng 'Har kuni ✅' tugmasini bosishingiz ham mumkin.",
        reply_markup=days_kb
    )

    await state.set_state(UserForm.waiting_for_days)


# --- 2-bosqich: kunlarni tanlash ---
@dp.message(UserForm.waiting_for_days)
async def get_days(message: types.Message, state: FSMContext):
    day = message.text.strip()
    valid_days = [
        "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
        "Juma", "Shanba", "Yakshanba", "Har kuni ✅"
    ]

    if day not in valid_days:
        await message.answer("❗ Iltimos, berilgan tugmalardan birini tanlang.")
        return

    await state.update_data(selected_days=day)
    await message.answer(
        "⏰ Endi aytingchi, sizga javob berish mumkin bo‘lgan vaqt oralig‘i?\n"
        "Masalan: 10:00 dan 19:00 gacha",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.set_state(UserForm.waiting_for_time)


# --- 3-bosqich: vaqt oralig‘i ---
@dp.message(UserForm.waiting_for_time)
async def get_time_range(message: types.Message, state: FSMContext):
    time_text = message.text.strip()
    if "dan" not in time_text or "gacha" not in time_text:
        await message.answer("❗ Iltimos, vaqtni to‘g‘ri formatda kiriting. Masalan: 10:00 dan 19:00 gacha")
        return

    await state.update_data(time_range=time_text)

    data = await state.get_data()
    user_id = message.from_user.id

    # Foydalanuvchi ma’lumotlarini saqlaymiz
    summary = (
        f"✅ Ma’lumotlaringiz saqlandi!\n\n"
        f"👤 Foydalanuvchi ID: {user_id}\n"
        f"💬 Xabar: {data.get('user_message')}\n"
        f"📅 Kunlar: {data.get('selected_days')}\n"
        f"⏰ Vaqt: {data.get('time_range')}\n\n"
        f"Sizning sozlamalaringiz faollashtirildi ✅"
    )

    await message.answer(summary)
    await state.clear()


# --- Botni ishga tushurish ---
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
