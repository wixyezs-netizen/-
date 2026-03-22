import asyncio
import logging
import sqlite3
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite

# ================== КОНФИГУРАЦИЯ ==================
API_TOKEN = "8624719452:AAHBAWy6DDzXD_ekK-iI8_rAOj4lUr3PysA"  # Замените на ваш токен
ADMIN_ID = 8346538289  # Замените на ваш Telegram ID
# =================================================

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)

# ================== РАБОТА С БАЗОЙ ДАННЫХ ==================
async def init_db():
    """Создание таблиц, если их нет"""
    async with aiosqlite.connect("users_data.db") as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                video_count INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP
            )
        ''')
        # Таблица видео
        await db.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_url TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                submitted_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        await db.commit()

async def get_user(user_id: int):
    """Получить информацию о пользователе"""
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute("SELECT video_count, is_completed FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def register_user(user_id: int, username: str, full_name: str):
    """Зарегистрировать нового пользователя"""
    async with aiosqlite.connect("users_data.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, video_count) VALUES (?, ?, ?, 0)",
            (user_id, username, full_name)
        )
        await db.commit()

async def add_video(user_id: int, video_url: str):
    """Добавить видео в базу"""
    async with aiosqlite.connect("users_data.db") as db:
        await db.execute(
            "INSERT INTO videos (user_id, video_url, submitted_at) VALUES (?, ?, ?)",
            (user_id, video_url, datetime.now())
        )
        await db.execute(
            "UPDATE users SET video_count = video_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
    
    # Проверяем, не выполнил ли пользователь задание
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute("SELECT video_count FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] >= 10:
                await db.execute(
                    "UPDATE users SET is_completed = 1, completed_at = ? WHERE user_id = ?",
                    (datetime.now(), user_id)
                )
                await db.commit()
                return True
    return False

async def get_pending_videos():
    """Получить все непроверенные видео"""
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute(
            "SELECT v.id, v.user_id, v.video_url, u.username, u.full_name, u.video_count "
            "FROM videos v JOIN users u ON v.user_id = u.user_id "
            "WHERE v.status = 'pending' ORDER BY v.submitted_at ASC"
        ) as cursor:
            return await cursor.fetchall()

async def update_video_status(video_id: int, status: str):
    """Обновить статус видео"""
    async with aiosqlite.connect("users_data.db") as db:
        await db.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            (status, video_id)
        )
        await db.commit()

async def get_user_videos(user_id: int):
    """Получить список видео пользователя"""
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute(
            "SELECT video_url, status FROM videos WHERE user_id = ? ORDER BY submitted_at DESC",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def reset_user_progress(user_id: int):
    """Сбросить прогресс пользователя (для выдачи доступа)"""
    async with aiosqlite.connect("users_data.db") as db:
        await db.execute(
            "UPDATE users SET video_count = 0, is_completed = 0, completed_at = NULL WHERE user_id = ?",
            (user_id,)
        )
        await db.execute(
            "DELETE FROM videos WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

# ================== СОСТОЯНИЯ FSM ==================
class VideoState(StatesGroup):
    waiting_for_link = State()

# ================== КЛАВИАТУРЫ ==================
def get_main_keyboard():
    """Главная клавиатура с кнопкой начала"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Начать задание", callback_data="start_task")]
    ])
    return keyboard

def get_admin_keyboard():
    """Клавиатура для админа"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить видео", callback_data="admin_check")]
    ])
    return keyboard

def get_video_actions_keyboard(video_id: int):
    """Клавиатура для проверки конкретного видео"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{video_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{video_id}")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_check")]
    ])
    return keyboard

# ================== ХЭНДЛЕРЫ ==================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    full_name = message.from_user.full_name
    
    await register_user(user_id, username, full_name)
    
    user_data = await get_user(user_id)
    
    if user_data:
        video_count = user_data[0]
        is_completed = user_data[1]
        
        if is_completed:
            await message.answer(
                f"✅ Привет, {full_name}! Ты уже выполнил задание и получил доступ.\n\n"
                f"Если ты потерял ключ, напиши администратору.",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                f"🎮 Привет, {full_name}!\n\n"
                f"Ты должен выложить 10 видео на YouTube и отправить ссылки мне.\n"
                f"📊 Твой прогресс: {video_count}/10\n\n"
                f"Нажми на кнопку ниже, чтобы начать загружать ссылки.",
                reply_markup=get_main_keyboard()
            )
    else:
        await message.answer(
            f"🎮 Привет, {full_name}!\n\n"
            f"Тебе нужно сделать 10 видео на YouTube и отправить ссылки.\n"
            f"После проверки я выдам чит и ключ.\n\n"
            f"Нажми на кнопку ниже, чтобы начать.",
            reply_markup=get_main_keyboard()
        )
    
    # Если это админ, показываем доп. кнопки
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "🔐 Админ-панель активна",
            reply_markup=get_admin_keyboard()
        )

@dp.callback_query(F.data == "start_task")
async def start_task(callback: CallbackQuery, state: FSMContext):
    """Начало задания - запрос ссылки"""
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    
    if user_data:
        video_count = user_data[0]
        is_completed = user_data[1]
        
        if is_completed:
            await callback.message.answer(
                "✅ Ты уже выполнил задание! Если у тебя проблемы, обратись к администратору."
            )
            await callback.answer()
            return
        
        if video_count >= 10:
            await callback.message.answer(
                "🎉 Поздравляю! Ты отправил все 10 видео. Администратор проверит их и свяжется с тобой."
            )
            await callback.answer()
            return
        
        await callback.message.answer(
            f"📹 Отправь ссылку на YouTube видео.\n"
            f"📊 Прогресс: {video_count}/10\n\n"
            f"⚠️ Важно: ссылка должна быть в формате:\n"
            f"https://youtu.be/... или https://www.youtube.com/watch?v=..."
        )
        await state.set_state(VideoState.waiting_for_link)
    else:
        await callback.message.answer("Произошла ошибка. Попробуй /start заново.")
    
    await callback.answer()

@dp.message(VideoState.waiting_for_link)
async def process_video_link(message: Message, state: FSMContext):
    """Обработка полученной ссылки"""
    user_id = message.from_user.id
    video_url = message.text.strip()
    
    # Простая валидация ссылки YouTube
    youtube_pattern = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
    if not re.match(youtube_pattern, video_url):
        await message.answer(
            "❌ Неверная ссылка! Пожалуйста, отправь корректную ссылку на YouTube видео.\n"
            "Пример: https://youtu.be/XXXXXXX или https://www.youtube.com/watch?v=XXXXXXX"
        )
        return
    
    # Добавляем видео в базу
    completed = await add_video(user_id, video_url)
    
    # Получаем текущий прогресс
    user_data = await get_user(user_id)
    video_count = user_data[0] if user_data else 0
    
    if completed:
        await message.answer(
            f"✅ Видео добавлено!\n"
            f"🎉 Поздравляю! Ты отправил все 10 видео!\n\n"
            f"Администратор проверит их и выдаст тебе доступ.\n"
            f"Ожидай ответа."
        )
        # Уведомляем админа
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🎉 Пользователь {message.from_user.full_name} (@{message.from_user.username}) "
                f"отправил все 10 видео! Можно проверить."
            )
    else:
        remaining = 10 - video_count
        await message.answer(
            f"✅ Видео добавлено!\n"
            f"📊 Прогресс: {video_count}/10\n"
            f"Осталось: {remaining}\n\n"
            f"Отправь следующую ссылку или нажми /start для главного меню."
        )
    
    await state.clear()

@dp.callback_query(F.data == "admin_check")
async def admin_check_videos(callback: CallbackQuery):
    """Показывает список непроверенных видео (только для админа)"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
    
    videos = await get_pending_videos()
    
    if not videos:
        await callback.message.answer("📭 Нет видео на проверку.")
        await callback.answer()
        return
    
    for video in videos:
        video_id, user_id, url, username, full_name, video_count = video
        
        text = (
            f"👤 Пользователь: {full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📊 Всего видео: {video_count}/10\n"
            f"🔗 Ссылка: {url}\n"
            f"━━━━━━━━━━━━━━━"
        )
        
        await callback.message.answer(
            text,
            reply_markup=get_video_actions_keyboard(video_id)
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_video(callback: CallbackQuery):
    """Одобрение видео"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    video_id = int(callback.data.split("_")[1])
    await update_video_status(video_id, "approved")
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Видео одобрено!",
        reply_markup=None
    )
    await callback.answer("Видео одобрено")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_video(callback: CallbackQuery):
    """Отклонение видео"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    video_id = int(callback.data.split("_")[1])
    await update_video_status(video_id, "rejected")
    
    # Получаем user_id для уведомления
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute("SELECT user_id FROM videos WHERE id = ?", (video_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                user_id = row[0]
                await bot.send_message(
                    user_id,
                    f"❌ Твое видео {video_id} было отклонено администратором.\n"
                    f"Пожалуйста, загрузи корректное видео и отправь ссылку снова."
                )
    
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ Видео отклонено!",
        reply_markup=None
    )
    await callback.answer("Видео отклонено")

@dp.callback_query(F.data == "admin_give_access")
async def give_access(callback: CallbackQuery):
    """Выдача доступа пользователю (админ выбирает из списка)"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    # Получаем всех пользователей, кто выполнил задание
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute(
            "SELECT user_id, username, full_name FROM users WHERE is_completed = 1"
        ) as cursor:
            users = await cursor.fetchall()
    
    if not users:
        await callback.message.answer("Нет пользователей, выполнивших задание.")
        await callback.answer()
        return
    
    # Создаем клавиатуру для выбора пользователя
    buttons = []
    for user_id, username, full_name in users:
        buttons.append([InlineKeyboardButton(
            text=f"{full_name} (@{username})",
            callback_data=f"give_key_{user_id}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("Выбери пользователя для выдачи ключа:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("give_key_"))
async def give_key_to_user(callback: CallbackQuery):
    """Выдача ключа выбранному пользователю"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[2])
    
    # Здесь вы можете вставить ваш ключ или ссылку на чит
    KEY_MESSAGE = (
        "🎉 Поздравляю! Твое задание выполнено.\n\n"
        "🔑 Вот твой доступ:\n"
        "Чит Standoff 2 0.37.1\n"
        "Ключ: STANDOFF2-2024-YOUR-KEY\n\n"
        "👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft"
    )
    
    await bot.send_message(user_id, KEY_MESSAGE)
    await callback.message.edit_text(f"✅ Ключ выдан пользователю!")
    await callback.answer("Ключ выдан")

# ================== ЗАПУСК БОТА ==================
async def main():
    await init_db()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
