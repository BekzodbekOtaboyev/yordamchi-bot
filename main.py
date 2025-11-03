import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8448499638:AAFFqtNvsU285I_dfvWCv_XpFxA_PSVxZr8"  # ← bu yerga tokenni yozing

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# --- Holatlar (FSM) ---
class UserForm(StatesGroup):
    target_choice = State()
    active_time_choice = State()
    user_message = State()
    week_days = State()
    start_time = State()
    end_time = State()
    manual_time = State()


# --- /start buyrug‘i ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()

    choice_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Faqat yangi yozganlarga")],
            [KeyboardButton(text="🌍 Barchaga yuborilsin")],
        ],
        resize_keyboard=True
    )

    await message.answer(
        "👋 Salom!\n\n"
        "Xabarni kimlarga yuborishni xohlaysiz?",
        reply_markup=choice_kb
    )
    await state.set_state(UserForm.target_choice)


# --- 1. Kimlarga yuborish tanlovi ---
@dp.message(UserForm.target_choice)
async def choose_target(message: types.Message, state: FSMContext):
    if message.text not in ["🆕 Faqat yangi yozganlarga", "🌍 Barchaga yuborilsin"]:
        await message.answer("❗ Iltimos, tugmalardan birini tanlang.")
        return

    await state.update_data(target_group=message.text)

    online_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💻 Faqat onlayn paytimda")],
            [KeyboardButton(text="⏱ Har doim ishlasin")],
        ],
        resize_keyboard=True
    )

    await message.answer(
        "⚙️ Bot qachon ishlasin?",
        reply_markup=online_kb
    )
    await state.set_state(UserForm.active_time_choice)


# --- 2. Ishlash vaqti (onlayn / har doim) ---
@dp.message(UserForm.active_time_choice)
async def choose_active_time(message: types.Message, state: FSMContext):
    if message.text not in ["💻 Faqat onlayn paytimda", "⏱ Har doim ishlasin"]:
        await message.answer("❗ Tugmalardan birini tanlang.")
        return

    await state.update_data(active_time=message.text)

    await message.answer(
        "✉️ Endi, o‘zingizning maxsus xabaringizni yozing (maksimum 2000 belgi):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(UserForm.user_message)


# --- 3. Foydalanuvchi xabari ---
@dp.message(UserForm.user_message)
async def get_user_message(message: types.Message, state: FSMContext):
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
        "📅 Haftaning qaysi kunlarida xabar yuborilsin?",
        reply_markup=days_kb
    )
    await state.set_state(UserForm.week_days)


# --- 4. Kun tanlash ---
@dp.message(UserForm.week_days)
async def choose_days(message: types.Message, state: FSMContext):
    day = message.text.strip()
    valid_days = [
        "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
        "Juma", "Shanba", "Yakshanba", "Har kuni ✅"
    ]
    if day not in valid_days:
        await message.answer("❗ Iltimos, berilgan tugmalardan birini tanlang.")
        return

    await state.update_data(selected_days=day)

    # soatlar ro‘yxati
    hours = [f"{str(h).zfill(2)}:00" for h in range(1, 24)]
    hour_buttons = [[KeyboardButton(text=h)] for h in hours]
    hour_buttons.append([KeyboardButton(text="🕓 Qo‘lda kiritaman")])
    hours_kb = ReplyKeyboardMarkup(keyboard=hour_buttons, resize_keyboard=True)

    await message.answer(
        "🕐 Xabar yuborilishi qaysi vaqtdan boshlansin?",
        reply_markup=hours_kb
    )
    await state.set_state(UserForm.start_time)


# --- 5. Boshlanish soati ---
@dp.message(UserForm.start_time)
async def choose_start_time(message: types.Message, state: FSMContext):
    time = message.text.strip()
    if time == "🕓 Qo‘lda kiritaman":
        await message.answer("⏰ Iltimos, vaqtni qo‘lda kiriting (masalan: 09:30):",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserForm.manual_time)
        return

    if not time.endswith(":00") or not time[:2].isdigit():
        await message.answer("❗ Iltimos, soatni to‘g‘ri tanlang yoki '🕓 Qo‘lda kiritaman' tugmasini bosing.")
        return

    await state.update_data(start_time=time)

    # tugash vaqt tugmalari
    hours = [f"{str(h).zfill(2)}:00" for h in range(1, 24)]
    hour_buttons = [[KeyboardButton(text=h)] for h in hours]
    hour_buttons.append([KeyboardButton(text="🕓 Qo‘lda kiritaman")])
    hours_kb = ReplyKeyboardMarkup(keyboard=hour_buttons, resize_keyboard=True)

    await message.answer("🕛 Endi xabar yuborilishi qaysi vaqtda tugasin?", reply_markup=hours_kb)
    await state.set_state(UserForm.end_time)


# --- 6. Tugash soati ---
@dp.message(UserForm.end_time)
async def choose_end_time(message: types.Message, state: FSMContext):
    time = message.text.strip()
    if time == "🕓 Qo‘lda kiritaman":
        await message.answer("⏰ Iltimos, vaqtni qo‘lda kiriting (masalan: 19:00):",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserForm.manual_time)
        return

    await state.update_data(end_time=time)

    data = await state.get_data()
    user_id = message.from_user.id

    summary = (
        "✅ Ma’lumotlaringiz saqlandi!\n\n"
        f"👤 ID: {user_id}\n"
        f"📩 Xabar: {data.get('user_message')}\n"
        f"🎯 Kimlarga: {data.get('target_group')}\n"
        f"⚙️ Ishlash: {data.get('active_time')}\n"
        f"📅 Kunlar: {data.get('selected_days')}\n"
        f"🕒 Boshlanish: {data.get('start_time')}\n"
        f"🕓 Tugash: {data.get('end_time')}\n\n"
        "Hammasi tayyor ✅"
    )

    await message.answer(summary, reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


# --- 7. Qo‘lda vaqt kiritish ---
@dp.message(UserForm.manual_time)
async def get_manual_time(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if ":" not in text:
        await message.answer("❗ Noto‘g‘ri format. Masalan: 10:30")
        return

    data = await state.get_data()

    if "start_time" not in data:
        await state.update_data(start_time=text)
        await message.answer("🕛 Endi tugash vaqtini kiriting (masalan: 19:00):")
    else:
        await state.update_data(end_time=text)
        data = await state.get_data()
        user_id = message.from_user.id

        summary = (
            "✅ Ma’lumotlaringiz saqlandi!\n\n"
            f"👤 ID: {user_id}\n"
            f"📩 Xabar: {data.get('user_message')}\n"
            f"🎯 Kimlarga: {data.get('target_group')}\n"
            f"⚙️ Ishlash: {data.get('active_time')}\n"
            f"📅 Kunlar: {data.get('selected_days')}\n"
            f"🕒 Boshlanish: {data.get('start_time')}\n"
            f"🕓 Tugash: {data.get('end_time')}\n\n"
            "Hammasi tayyor ✅"
        )

        await message.answer(summary)
        await state.clear()


# --- Ishga tushirish ---
async def main():
    print("🤖 DLS REKLAMA BOT ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
