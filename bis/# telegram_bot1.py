import asyncio
import logging
import os
from datetime import datetime, timedelta
from aiogram.types import FSInputFile

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite


BOT_TOKEN = "--------"
ADMIN_ID = ------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "presentation.pdf")

TARIFF_DAYS = {
    "Basic": 30,
    "Premium": 90,
}

TEXTS = {
    "start": (
        "🎉 Добро пожаловать в наш сервис!\n\n"
        "Здесь вы можете выбрать подходящий тариф и начать пользоваться всеми преимуществами.\n\n"
        "📋 Презентация сервиса прикреплена ниже 👇"
    ),
    "main_menu": "🏠 Главное меню – выберите действие:",
    "about_service": (
        "ℹ️ О сервисе\n\n"
        "Наш сервис предоставляет профессиональные решения для вашего бизнеса.\n\n"
        "✨ Основные преимущества:\n"
        "• 100% надежность\n"
        "• Удобный интерфейс\n"
        "• Поддержка 24/7\n\n"
        "👇 Выберите подходящий тариф!"
    ),
    "basic_tariff": (
        "💎 Тариф Basic – 50 ⭐\n\n"
        "📱 Базовый функционал:\n"
        "• Доступ ко всем основным функциям\n"
        "• Поддержка 24/7\n"
        "• 100 ГБ хранилища\n"
        "• Действует 30 дней\n\n"
        "💰 Стоимость: 50 Telegram Stars\n\n"
        "👇 Нажмите «Оплатить» для активации"
    ),
    "premium_tariff": (
        "👑 Тариф Premium – 200 ⭐\n\n"
        "⭐ Премиум возможности:\n"
        "• Всё из Basic\n"
        "• Приоритетная поддержка\n"
        "• Неограниченное хранилище\n"
        "• Эксклюзивные функции\n"
        "• Персональный менеджер\n"
        "• Действует 90 дней\n\n"
        "💰 Стоимость: 200 Telegram Stars\n\n"
        "👇 Нажмите «Оплатить» для активации"
    ),
    "payment_success": (
        "✅ Платеж успешно завершен!\n\n"
        "🎉 Тариф {tariff} активирован!\n"
        "📅 Дата покупки: {date}\n"
        "⏰ Действует до: {expires}\n"
        "💰 Сумма: {amount} ⭐\n\n"
        "🚀 Теперь вы можете пользоваться всеми возможностями!\n"
        "Спасибо за выбор нашего сервиса! ✨"
    ),
    "no_tariffs": "📭 У вас нет активных тарифов\n\n💡 Нажмите на тариф ниже!",
    "support": "💬 Связь с поддержкой\n\nНапишите нам напрямую 👇",
}

async def init_db():
    async with aiosqlite.connect("bot_payments.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tariff TEXT,
                amount INTEGER,
                payment_id TEXT UNIQUE,
                purchase_date TEXT,
                expires_date TEXT
            )
        """)
        await db.commit()

async def save_payment(user_id: int, tariff: str, amount: int, payment_id: str):
    purchase_date = datetime.now()
    expires_date = purchase_date + timedelta(days=TARIFF_DAYS[tariff])
    async with aiosqlite.connect("bot_payments.db") as db:
        await db.execute("""
            INSERT INTO payments (user_id, tariff, amount, payment_id, purchase_date, expires_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, tariff, amount, payment_id, purchase_date.isoformat(), expires_date.isoformat()))
        await db.commit()
    return expires_date

async def get_user_active_tariff(user_id: int):
    try:
        async with aiosqlite.connect("bot_payments.db") as db:
            async with db.execute("""
                SELECT tariff, amount, purchase_date, expires_date
                FROM payments
                WHERE user_id = ? AND datetime(expires_date) > datetime('now')
                ORDER BY purchase_date DESC LIMIT 1
            """, (user_id,)) as cursor:
                return await cursor.fetchone()
    except:
        return None


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about")],
        [
            InlineKeyboardButton(text="💎 Тариф Basic", callback_data="basic"),
            InlineKeyboardButton(text="👑 Тариф Premium", callback_data="premium"),
        ],
        [InlineKeyboardButton(text="📋 Мои тарифы", callback_data="my_tariffs")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
    ])

def get_tariff_keyboard(tariff: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_{tariff}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])

def get_back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])


router = Router()
logging.basicConfig(level=logging.INFO)

@router.message(CommandStart())
async def cmd_start(message: Message):
    logging.info(f"Рабочая директория: {os.getcwd()}")
    logging.info(f"PDF существует: {os.path.exists(PDF_PATH)}")

    await message.answer(TEXTS["start"])

    if os.path.exists(PDF_PATH):
        try:
            pdf_file = FSInputFile(PDF_PATH)
     
            await message.answer_document(
                document=pdf_file,
                caption="📋 Презентация сервиса"
            )
     
            await message.answer("🏠 Главное меню:", reply_markup=get_main_menu())
            logging.info("✅ PDF + МЕНЮ отправлены отдельно")
            return
        except Exception as e:
            logging.error(f"Ошибка PDF: {e}")

    await message.answer("🏠 Главное меню:", reply_markup=get_main_menu())

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("🏠 Главное меню:", reply_markup=get_main_menu())

@router.message(Command("pdf"))
async def cmd_pdf(message: Message):
    if os.path.exists(PDF_PATH):
        try:
            pdf_file = FSInputFile(PDF_PATH)
            await message.answer_document(pdf_file, caption="🔥 PDF тест")
        except Exception as e:
            await message.answer(f"❌ Ошибка PDF: {e}")
    else:
        await message.answer("❌ PDF не найден")


@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    await callback.message.answer(TEXTS["main_menu"], reply_markup=get_main_menu())
    await callback.answer()

@router.callback_query(F.data == "about")
async def process_about(callback: CallbackQuery):
    await callback.message.answer(TEXTS["about_service"], reply_markup=get_back_to_menu())
    await callback.answer()

@router.callback_query(F.data == "basic")
async def process_basic(callback: CallbackQuery):
    await callback.message.answer(TEXTS["basic_tariff"], reply_markup=get_tariff_keyboard("basic"))
    await callback.answer()

@router.callback_query(F.data == "premium")
async def process_premium(callback: CallbackQuery):
    await callback.message.answer(TEXTS["premium_tariff"], reply_markup=get_tariff_keyboard("premium"))
    await callback.answer()

@router.callback_query(F.data == "my_tariffs")
async def process_my_tariffs(callback: CallbackQuery):
    active = await get_user_active_tariff(callback.from_user.id)
    text = TEXTS["no_tariffs"] if not active else f"✅ Активный тариф: {active[0]}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Тариф Basic", callback_data="basic")],
        [InlineKeyboardButton(text="👑 Тариф Premium", callback_data="premium")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "support")
async def process_support(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Поддержка", url=f"https://t.me/{ADMIN_ID}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])
    await callback.message.answer(TEXTS["support"], reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    code = callback.data.split("_")[1]
    if code == "basic":
        title = "Тариф Basic"
        payload = "basic"
        prices = [LabeledPrice(label="Тариф Basic", amount=50)]
    elif code == "premium":
        title = "Тариф Premium"
        payload = "premium"
        prices = [LabeledPrice(label="Тариф Premium", amount=200)]
    else:
        await callback.answer("Ошибка тарифа")
        return
    
    await callback.message.answer_invoice(
        title=title,
        description=TEXTS[f"{code}_tariff"],
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    tariff = "Basic" if message.successful_payment.invoice_payload == "basic" else "Premium"
    amount = 50 if tariff == "Basic" else 200
    await save_payment(message.from_user.id, tariff, amount, message.successful_payment.telegram_payment_charge_id)
    await message.answer(f"✅ {tariff} активирован!", reply_markup=get_main_menu())

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await init_db()
    print("🚀 Бот запущен! PDF + КНОПКИ работают!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


