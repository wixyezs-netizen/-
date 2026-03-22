import asyncio
import logging
import re
import sqlite3
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

# ТЕКСТЫ ДЛЯ ЗАДАНИЯ
TASK_DESCRIPTION = """
📋 **ИНСТРУКЦИЯ ПО ВЫПОЛНЕНИЮ ЗАДАНИЯ**

1️⃣ **Где брать видео?**
   - Берете видео с TikTok из Telegram каналов с читом Standoff 2 0.37.1
   - Видео должны быть БЕЗ водяных знаков и тегов

2️⃣ **Как выкладывать на YouTube?**
   - Загружаете видео как ОБЫЧНЫЙ ролик (НЕ Шортс)
   - Вставляете название (кнопка ниже)
   - Вставляете описание (кнопка ниже)
   - В комментариях оставляете ссылку на Telegram канал (кнопка ниже)

3️⃣ **Что нужно сделать?**
   - Выложить 10 разных видео
   - После каждого видео отправить ссылку боту
   - После 10 видео я проверю и выдам чит + ключ

⚠️ **ВАЖНО!** Без ссылки в комментариях не будет выдачи софта!
"""

VIDEO_TITLE = "⚡️КАК СКАЧАТЬ ЧИТ 0.37.1 STANDOFF 2 БЕЗ РУТ И БАНА ПОЛНАЯ УСТАНОВКА"

VIDEO_DESCRIPTION = """
⚡️КАК СКАЧАТЬ ЧИТ 0.37.1 STANDOFF 2 БЕЗ РУТ И БАНА ПОЛНАЯ УСТАНОВКА

👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft

#standoff2 #стандофф2 #чит #standoff2чит #стандофф2чит
"""

COMMENT_TEXT = "👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft"

TAGS = """
standoff 2, стандофф, standoff, стендофф, standoff2, веля, стендофф 2, стэндофф 2, стендоф, стэндофф, standof, стандофф2, стандоф, рик, обнова 0.37.1, обновление 0.37.1, kasai_standoff2, стандофф обновление, со2, so2, стандоф 2, стендофф2, 0.37.1 стандофф 2, стендов, стандофф 2 0.37.1, 0.37.1, в стандофф 2, standoff 2 0.37.1, ric, скрафтил аркану, крафт стандофф 2, мем стандофф, мем стандофф 2, девушка в стандофф 2, wonderfull shorts, софт касай, казашка, kazashka, мафиозник, kasai софт, kasai shorts, fragmovie standoff, фрагмуви стандофф, apollon standoff 2, apollon shorts, казашка стандофф 2, мафиозник и казашка, мемы стандофф 2, мемы стандофф 2 шортс, мемы стандофф 2 без мата, смешные моменты стандофф 2, стандофф 2 мемы шортс, юкан, шортс, казашка standoff 2, казашка стандофф, девушка играет в стандофф, shorts, крафт арканы standoff 2, standoff 2 full allies gameplay, лучший игрок на телефоне в стандофф 2, fragmovie standoff 2, мувик стандофф 2, ipad pro 2020 standoff 2, айфон 7 стандофф 2, ipad pro 2021 standoff 2, frontos, лучший игрок с телефона standoff 2, мувики стандофф 2, фрагмуви стандофф 2, standoff 2 fragmovie, #h9ije, айпад 9 стандофф 2, стандофф 2 фрагмуви, стандофф 2 мувик, h9nto, айпад 2021 стандофф 2, ipad pro 2018 standoff 2, best player standoff 2, en9rjee so2, h9ije standoff 2, m9 bayonet standoff 2, стендоф 2, обзор обновления 0.37.1, standoff 2 allies legend, standoff 2 allies gameplay, standoff 2 full competitive match gameplay, standoff 2 competitive gameplay, lilith so2, standoff 2 allies, standoff 2 ranked, standoff 2 settings, standoff 2 competitive, мувик, lilith so2 allies, девушка, сталофф, belka, веля standoff 2, веля стандофф 2, стандофы, со, белка, тик так, керамбит голд, как скрафтить ориджин коллекцию, читы стандофф2, hacking, root, ipa, cheating, cheats, hack, hacks, cheat, кент апк, kent.apk, видео, тиктак стрим, стримы, tictac, тиктак, standoff 2 0.37.1, standoff 0.37.1, скачать 0.37.1, стандофф 2 читы, стандофф 2 читы на телефон, как скачать читы на стандофф 2, чит стандофф 2, как скачать читы на стандофф 2 0.37.1, читы стандофф 2, чит на стандофф, стандофф 2 чит, чит на standoff 2, standoff 2 читы, скачать читы на стандофф 2, standoff 2 чит, как скачать читы на standoff 2 0.37.1, чит на standoff 2 0.37.1, читы на standoff 2, читы standoff 2, читы на стандофф 2 0.37.1, чит на стандофф 2, читы на standoff 2 0.37.1, standoff читы, раш, дата новогоднего обновления, читыстандофф, прикол, приколы, читы на стандофф 2, читы, косай, косой, wonderfull, приколыстандофф, приколыстандофф2, шерлок стандофф, 0.37.1, фрагмуви, шерлок standoff2, шерлок, обновление, обнова стандофф, эйс, kasai_standoff, касай_стандофф, дата выхода обновления 0.37.1, обновление в плей маркете, axlebolt, новогоднее обновление 0.37.1, скачать обновление, дата 0.37.1, что добавят 0.37.1, мамонт, купил аккаунты
"""

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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_url TEXT,
                status TEXT DEFAULT 'pending',
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

# ================== СОСТОЯНИЯ FSM ==================
class VideoState(StatesGroup):
    waiting_for_link = State()

# ================== КЛАВИАТУРЫ ==================
def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Посмотреть задание", callback_data="show_task")],
        [InlineKeyboardButton(text="📝 Получить данные для видео", callback_data="get_data")],
        [InlineKeyboardButton(text="📤 Отправить ссылку на видео", callback_data="send_link")],
        [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="show_progress")]
    ])
    return keyboard

def get_admin_keyboard():
    """Клавиатура для админа"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить видео", callback_data="admin_check")],
        [InlineKeyboardButton(text="🎁 Выдать ключ", callback_data="admin_give_access")]
    ])
    return keyboard

def get_video_actions_keyboard(video_id: int):
    """Клавиатура для проверки видео"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{video_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{video_id}")
        ],
        [InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_check")]
    ])
    return keyboard

def get_data_keyboard():
    """Клавиатура для выдачи данных"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название видео", callback_data="copy_title")],
        [InlineKeyboardButton(text="📄 Описание видео", callback_data="copy_description")],
        [InlineKeyboardButton(text="💬 Комментарий", callback_data="copy_comment")],
        [InlineKeyboardButton(text="🏷️ Теги (для описания)", callback_data="copy_tags")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
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
    
    welcome_text = (
        f"🎮 **Привет, {full_name}!**\n\n"
        f"Я помогу тебе выполнить задание и получить чит Standoff 2 0.37.1\n\n"
        f"Выбери действие на кнопках ниже:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    
    # Если это админ, показываем админ-панель
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "🔐 **Админ-панель активирована**",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "show_task")
async def show_task(callback: CallbackQuery):
    """Показать задание"""
    await callback.message.answer(
        TASK_DESCRIPTION,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "get_data")
async def get_data(callback: CallbackQuery):
    """Показать данные для видео"""
    await callback.message.answer(
        "📋 **Выбери, что тебе нужно:**\n\n"
        "• **Название** - скопируй и вставь в заголовок видео\n"
        "• **Описание** - вставь в описание видео\n"
        "• **Комментарий** - оставь под видео\n"
        "• **Теги** - добавь в описание для продвижения",
        parse_mode="Markdown",
        reply_markup=get_data_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "copy_title")
async def copy_title(callback: CallbackQuery):
    """Выдать название видео"""
    await callback.message.answer(
        f"📝 **Название видео:**\n\n"
        f"`{VIDEO_TITLE}`\n\n"
        f"Нажми на текст, чтобы скопировать",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "copy_description")
async def copy_description(callback: CallbackQuery):
    """Выдать описание видео"""
    await callback.message.answer(
        f"📄 **Описание видео:**\n\n"
        f"```\n{VIDEO_DESCRIPTION}\n```\n\n"
        f"Нажми на текст, чтобы скопировать",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "copy_comment")
async def copy_comment(callback: CallbackQuery):
    """Выдать текст комментария"""
    await callback.message.answer(
        f"💬 **Текст для комментария:**\n\n"
        f"`{COMMENT_TEXT}`\n\n"
        f"⚠️ **ВАЖНО!** Обязательно оставь этот комментарий под видео!\n"
        f"Без него я не выдам доступ!",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "copy_tags")
async def copy_tags(callback: CallbackQuery):
    """Выдать теги"""
    await callback.message.answer(
        f"🏷️ **Теги для видео:**\n\n"
        f"```\n{TAGS}\n```\n\n"
        f"Скопируй эти теги и добавь в описание видео",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.answer(
        "🎮 **Главное меню**",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "send_link")
async def send_link_prompt(callback: CallbackQuery, state: FSMContext):
    """Начать отправку ссылки"""
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    
    if user_data:
        video_count = user_data[0]
        is_completed = user_data[1]
        
        if is_completed:
            await callback.message.answer(
                "✅ Ты уже выполнил задание! Ожидай проверки администратором."
            )
            await callback.answer()
            return
        
        if video_count >= 10:
            await callback.message.answer(
                "🎉 Ты отправил все 10 видео! Администратор проверит их и выдаст доступ."
            )
            await callback.answer()
            return
        
        await callback.message.answer(
            f"📹 **Отправь ссылку на YouTube видео**\n\n"
            f"📊 Твой прогресс: {video_count}/10\n\n"
            f"⚠️ Ссылка должна быть в формате:\n"
            f"`https://youtu.be/XXXXXXX` или `https://www.youtube.com/watch?v=XXXXXXX`\n\n"
            f"После отправки ссылки видео будет добавлено на проверку.",
            parse_mode="Markdown"
        )
        await state.set_state(VideoState.waiting_for_link)
    else:
        await callback.message.answer("Ошибка! Попробуй /start")
    
    await callback.answer()

@dp.callback_query(F.data == "show_progress")
async def show_progress(callback: CallbackQuery):
    """Показать прогресс пользователя"""
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    
    if user_data:
        video_count = user_data[0]
        is_completed = user_data[1]
        
        progress_bar = "▰" * video_count + "▱" * (10 - video_count)
        
        if is_completed:
            status = "✅ Задание выполнено! Ожидай проверки."
        else:
            status = f"⏳ Осталось: {10 - video_count} видео"
        
        await callback.message.answer(
            f"📊 **Твой прогресс:**\n\n"
            f"`{progress_bar}`\n"
            f"**{video_count}/10 видео**\n\n"
            f"{status}",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer("Ошибка! Попробуй /start")
    
    await callback.answer()

@dp.message(VideoState.waiting_for_link)
async def process_video_link(message: Message, state: FSMContext):
    """Обработка полученной ссылки"""
    user_id = message.from_user.id
    video_url = message.text.strip()
    
    # Валидация YouTube ссылки
    youtube_pattern = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
    if not re.match(youtube_pattern, video_url):
        await message.answer(
            "❌ **Неверная ссылка!**\n\n"
            "Отправь корректную ссылку на YouTube видео.\n"
            "Примеры:\n"
            "`https://youtu.be/XXXXXXX`\n"
            "`https://www.youtube.com/watch?v=XXXXXXX`",
            parse_mode="Markdown"
        )
        return
    
    completed = await add_video(user_id, video_url)
    user_data = await get_user(user_id)
    video_count = user_data[0] if user_data else 0
    
    if completed:
        await message.answer(
            f"✅ **Видео добавлено!**\n\n"
            f"🎉 **Поздравляю! Ты отправил все 10 видео!**\n\n"
            f"Администратор проверит их и выдаст тебе доступ.\n"
            f"Ожидай ответа в ближайшее время.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🎉 **НОВОЕ ВЫПОЛНЕНИЕ!**\n\n"
                f"Пользователь {message.from_user.full_name} (@{message.from_user.username})\n"
                f"отправил все 10 видео!\n"
                f"ID: {user_id}",
                parse_mode="Markdown"
            )
    else:
        remaining = 10 - video_count
        await message.answer(
            f"✅ **Видео добавлено!**\n\n"
            f"📊 **Прогресс:** {video_count}/10\n"
            f"⏳ **Осталось:** {remaining} видео\n\n"
            f"Отправь следующую ссылку или нажми /start для главного меню.",
            parse_mode="Markdown"
        )
    
    await state.clear()

# ================== АДМИН-ХЭНДЛЕРЫ ==================
@dp.callback_query(F.data == "admin_check")
async def admin_check_videos(callback: CallbackQuery):
    """Показать видео на проверку"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    videos = await get_pending_videos()
    
    if not videos:
        await callback.message.answer("📭 Нет видео на проверку.")
        await callback.answer()
        return
    
    await callback.message.answer(f"🔍 **На проверке: {len(videos)} видео**", parse_mode="Markdown")
    
    for video in videos:
        video_id, user_id, url, username, full_name, video_count = video
        
        text = (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Пользователь:** {full_name}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📊 **Всего видео:** {video_count}/10\n"
            f"🔗 **Ссылка:** {url}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_video_actions_keyboard(video_id)
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_video(callback: CallbackQuery):
    """Одобрить видео"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    video_id = int(callback.data.split("_")[1])
    await update_video_status(video_id, "approved")
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ **Видео одобрено!**",
        parse_mode="Markdown"
    )
    await callback.answer("Видео одобрено")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_video(callback: CallbackQuery):
    """Отклонить видео"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    video_id = int(callback.data.split("_")[1])
    await update_video_status(video_id, "rejected")
    
    # Получаем user_id
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute("SELECT user_id FROM videos WHERE id = ?", (video_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                user_id = row[0]
                await bot.send_message(
                    user_id,
                    f"❌ **Видео отклонено!**\n\n"
                    f"Причина: несоответствие требованиям.\n\n"
                    f"Пожалуйста, загрузи корректное видео и отправь ссылку снова.\n"
                    f"Требования:\n"
                    f"• Видео без водяных знаков\n"
                    f"• Название как в инструкции\n"
                    f"• Описание как в инструкции\n"
                    f"• Комментарий со ссылкой",
                    parse_mode="Markdown"
                )
    
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ **Видео отклонено!**",
        parse_mode="Markdown"
    )
    await callback.answer("Видео отклонено")

@dp.callback_query(F.data == "admin_give_access")
async def give_access_menu(callback: CallbackQuery):
    """Меню выдачи доступа"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    async with aiosqlite.connect("users_data.db") as db:
        async with db.execute(
            "SELECT user_id, username, full_name FROM users WHERE is_completed = 1"
        ) as cursor:
            users = await cursor.fetchall()
    
    if not users:
        await callback.message.answer("📭 Нет пользователей, выполнивших задание.")
        await callback.answer()
        return
    
    buttons = []
    for user_id, username, full_name in users:
        buttons.append([InlineKeyboardButton(
            text=f"🎁 {full_name} (@{username})",
            callback_data=f"give_key_{user_id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_check")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(
        "🎁 **Выбери пользователя для выдачи ключа:**",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("give_key_"))
async def give_key_to_user(callback: CallbackQuery):
    """Выдать ключ пользователю"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[2])
    
    KEY_MESSAGE = (
        "🎉 **Поздравляю! Ты выполнил задание!**\n\n"
        "🔑 **Вот твой доступ:**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "**Чит Standoff 2 0.37.1**\n"
        "**Ключ:** `STANDOFF2-2024-ACTIVE-KEY`\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "👉 **СКАЧАТЬ ТУТ ТГК:** https://t.me/AimNooBsoft\n\n"
        "📌 Инструкция по установке в канале!"
    )
    
    await bot.send_message(user_id, KEY_MESSAGE, parse_mode="Markdown")
    await callback.message.edit_text(f"✅ **Ключ выдан пользователю!**")
    await callback.answer("Ключ выдан!")

# ================== ЗАПУСК БОТА ==================
async def main():
    await init_db()
    print("🤖 Бот запущен!")
    print(f"📱 Админ ID: {ADMIN_ID}")
    print("✅ Готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
