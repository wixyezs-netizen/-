"""
Telegram Mini App для AimNoob Bot
Всё в одном файле: FastAPI backend + Telegram Bot + HTML/CSS/JS frontend
"""

import os
import json
import hmac
import hashlib
import logging
import secrets
import asyncio
from datetime import datetime
from urllib.parse import parse_qs, unquote

import aiosqlite
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import threading

# ================== КОНФИГУРАЦИЯ ==================
API_TOKEN = "8624719452:AAHBAWy6DDzXD_ekK-iI8_rAOj4lUr3PysA"
BOT_TOKEN = API_TOKEN
DB_PATH = "users_data.db"
REQUIRED_VIDEOS = 10
DOMAIN = "AimMani.bothost.tech"
CHANNEL_LINK = "https://t.me/AimNooBsoft"
DOWNLOAD_LINK = "https://go.linkify.ru/2GPF"
WEBAPP_URL = f"https://{DOMAIN}"

# Данные для видео
VIDEO_TITLE = "Чит для Standoff 2 0.37.1 | Скачать AimNoob 2025"
VIDEO_DESCRIPTION = """Скачать чит для Standoff 2 0.37.1: https://t.me/AimNooBsoft

🔥 Функции чита:
• Аимбот с настройками
• Wallhack (стены)
• ESP игроков
• No Recoil
• Автоматическая стрельба
• И многое другое!

✅ Работает на всех версиях Android
✅ Без вирусов и банов
✅ Регулярные обновления

Подпишись на канал: https://t.me/AimNooBsoft
#standoff2 #чит #aimbot #wallhack #standoff2чит #aimnoob"""
COMMENT_TEXT = "Скачать чит Standoff 2: https://t.me/AimNooBsoft"
TAGS = "standoff2, чит standoff2, скачать чит standoff2, standoff2 aimbot, standoff2 wallhack, aimnoob, чит на андроид, standoff2 0.37.1, standoff2 читы, aimbot standoff2"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== ИНИЦИАЛИЗАЦИЯ ==================
app = FastAPI(title="AimNoob Mini App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram Bot
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ================== СОСТОЯНИЯ FSM ==================
class AddVideo(StatesGroup):
    waiting_for_url = State()


# ================== БАЗА ДАННЫХ ==================
async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                video_count INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                key_issued INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица видео
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_url TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица выданных ключей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS issued_keys (
                user_id INTEGER PRIMARY KEY,
                key_value TEXT,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        await db.commit()
        logger.info("Database initialized")


async def get_user_data(user_id: int) -> dict:
    """Получить данные пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                user = dict(row)
            else:
                user = {
                    "user_id": user_id,
                    "video_count": 0,
                    "is_completed": 0,
                    "key_issued": 0,
                    "is_banned": 0,
                    "registered_at": None,
                    "full_name": None,
                    "username": None,
                }

        # Получаем ключ
        async with db.execute(
            "SELECT key_value FROM issued_keys WHERE user_id = ?",
            (user_id,)
        ) as cur:
            key_row = await cur.fetchone()
            user["key"] = key_row[0] if key_row else None

        # Получаем видео
        async with db.execute(
            "SELECT * FROM videos WHERE user_id = ? ORDER BY submitted_at ASC",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            user["videos"] = [dict(r) for r in rows]

    return user


async def get_or_create_user(user_id: int, full_name: str = None, username: str = None):
    """Получить или создать пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            
            if not user:
                await db.execute("""
                    INSERT INTO users (user_id, full_name, username)
                    VALUES (?, ?, ?)
                """, (user_id, full_name, username))
                await db.commit()
                return {
                    "user_id": user_id,
                    "full_name": full_name,
                    "username": username,
                    "video_count": 0,
                    "is_completed": 0,
                    "key_issued": 0,
                    "is_banned": 0
                }
            else:
                return {
                    "user_id": user[0],
                    "full_name": user[1],
                    "username": user[2],
                    "video_count": user[3],
                    "is_completed": user[4],
                    "key_issued": user[5],
                    "is_banned": user[6]
                }


async def add_video(user_id: int, video_url: str):
    """Добавить видео для проверки"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Добавляем видео
        await db.execute("""
            INSERT INTO videos (user_id, video_url, status)
            VALUES (?, ?, 'pending')
        """, (user_id, video_url))
        
        # Обновляем счетчик видео
        await db.execute("""
            UPDATE users 
            SET video_count = video_count + 1
            WHERE user_id = ?
        """, (user_id,))
        
        # Проверяем, достиг ли пользователь лимита
        async with db.execute(
            "SELECT video_count FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            
            if count >= REQUIRED_VIDEOS:
                await db.execute("""
                    UPDATE users SET is_completed = 1
                    WHERE user_id = ?
                """, (user_id,))
        
        await db.commit()
        return count


async def issue_key(user_id: int):
    """Выдать ключ пользователю"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, есть ли уже ключ
        async with db.execute(
            "SELECT key_value FROM issued_keys WHERE user_id = ?", (user_id,)
        ) as cursor:
            if await cursor.fetchone():
                return None
        
        # Генерируем ключ
        key = f"AIM-{secrets.token_hex(8).upper()}"
        
        # Сохраняем ключ
        await db.execute("""
            INSERT INTO issued_keys (user_id, key_value)
            VALUES (?, ?)
        """, (user_id, key))
        
        # Обновляем статус пользователя
        await db.execute("""
            UPDATE users SET key_issued = 1
            WHERE user_id = ?
        """, (user_id,))
        
        await db.commit()
        return key


async def get_stats() -> dict:
    """Получить статистику"""
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        queries = {
            "total_users": "SELECT COUNT(*) FROM users",
            "completed": "SELECT COUNT(*) FROM users WHERE is_completed = 1",
            "keys_issued": "SELECT COUNT(*) FROM issued_keys",
            "total_videos": "SELECT COUNT(*) FROM videos",
            "pending": "SELECT COUNT(*) FROM videos WHERE status = 'pending'",
            "approved": "SELECT COUNT(*) FROM videos WHERE status = 'approved'",
            "rejected": "SELECT COUNT(*) FROM videos WHERE status = 'rejected'",
        }
        for key, query in queries.items():
            async with db.execute(query) as c:
                stats[key] = (await c.fetchone())[0]
    return stats


async def get_leaderboard() -> list:
    """Получить таблицу лидеров"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, full_name, username, video_count, "
            "is_completed, key_issued FROM users "
            "WHERE is_banned = 0 AND video_count > 0 "
            "ORDER BY video_count DESC, registered_at ASC LIMIT 50"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ================== КЛАВИАТУРЫ ТЕЛЕГРАМ ==================
def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Открыть Mini App",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/app")
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Моя статистика",
                    callback_data="stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📹 Отправить видео",
                    callback_data="add_video"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔑 Получить ключ",
                    callback_data="get_key"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📌 Наш канал",
                    url=CHANNEL_LINK
                )
            ]
        ]
    )
    return keyboard


# ================== ОБРАБОТЧИКИ ТЕЛЕГРАМ ==================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = await get_or_create_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    
    welcome_text = (
        f"🎯 <b>Добро пожаловать, {message.from_user.first_name}!</b>\n\n"
        f"Этот бот поможет тебе получить ключ для чита Standoff 2.\n\n"
        f"📋 <b>Как получить ключ:</b>\n"
        f"1️⃣ Найди 10 видео (тема: чит Standoff 2)\n"
        f"2️⃣ Загрузи их на YouTube (НЕ Shorts)\n"
        f"3️⃣ Отправь ссылки боту\n"
        f"4️⃣ Получи уникальный ключ активации!\n\n"
        f"📊 <b>Твой прогресс:</b> {user['video_count']}/{REQUIRED_VIDEOS}\n\n"
        f"👇 <b>Нажми на кнопку ниже, чтобы начать!</b>"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
    """Показать статистику"""
    user = await get_or_create_user(callback.from_user.id)
    
    stats_text = (
        f"📊 <b>Твоя статистика</b>\n\n"
        f"🎯 Отправлено видео: <b>{user['video_count']}/{REQUIRED_VIDEOS}</b>\n"
        f"✅ Задание выполнено: {'Да' if user['is_completed'] else 'Нет'}\n"
        f"🔑 Ключ получен: {'Да' if user['key_issued'] else 'Нет'}\n"
        f"🚫 Статус: {'Заблокирован' if user['is_banned'] else 'Активен'}"
    )
    
    await callback.answer()
    await callback.message.answer(stats_text, parse_mode="HTML")


@dp.callback_query(F.data == "add_video")
async def callback_add_video(callback: types.CallbackQuery, state: FSMContext):
    """Начать добавление видео"""
    user = await get_or_create_user(callback.from_user.id)
    
    if user['is_banned']:
        await callback.answer("❌ Ваш аккаунт заблокирован!", show_alert=True)
        return
    
    if user['key_issued']:
        await callback.answer("✅ Вы уже получили ключ!", show_alert=True)
        return
    
    if user['is_completed']:
        remaining = "ожидает проверки"
    else:
        remaining = f"{REQUIRED_VIDEOS - user['video_count']} видео"
    
    await callback.answer()
    await callback.message.answer(
        f"📹 <b>Отправь ссылку на YouTube видео</b>\n\n"
        f"Осталось отправить: {remaining}\n\n"
        f"<i>Ссылка должна быть в формате:\n"
        f"https://youtu.be/... или https://www.youtube.com/...</i>\n\n"
        f"📌 <b>Важно:</b> В описании видео обязательно должна быть ссылка на наш канал!\n"
        f"{CHANNEL_LINK}",
        parse_mode="HTML"
    )
    
    await state.set_state(AddVideo.waiting_for_url)


@dp.message(AddVideo.waiting_for_url, F.text)
async def process_video_url(message: types.Message, state: FSMContext):
    """Обработка отправленной ссылки"""
    user = await get_or_create_user(message.from_user.id)
    url = message.text.strip()
    
    # Простая проверка URL
    if not (url.startswith("https://youtu.be/") or 
            url.startswith("https://www.youtube.com/watch?v=") or
            url.startswith("https://youtube.com/watch?v=")):
        await message.answer(
            "❌ <b>Неверный формат ссылки!</b>\n\n"
            "Пожалуйста, отправь ссылку в формате:\n"
            "https://youtu.be/... или https://www.youtube.com/...",
            parse_mode="HTML"
        )
        return
    
    if user['key_issued']:
        await message.answer("✅ Вы уже получили ключ!")
        await state.clear()
        return
    
    if user['is_completed']:
        await message.answer(
            "✅ Вы уже отправили все 10 видео!\n"
            "Ожидайте проверки администратором."
        )
        await state.clear()
        return
    
    # Сохраняем видео
    video_count = await add_video(message.from_user.id, url)
    
    await message.answer(
        f"✅ <b>Видео принято!</b>\n\n"
        f"📊 Прогресс: {video_count}/{REQUIRED_VIDEOS}\n\n"
        f"{'🎉 Поздравляю! Ты выполнил задание! Ожидай проверки.' if video_count >= REQUIRED_VIDEOS else 'Продолжай в том же духе!'}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    
    await state.clear()


@dp.callback_query(F.data == "get_key")
async def callback_get_key(callback: types.CallbackQuery):
    """Получить ключ"""
    user = await get_or_create_user(callback.from_user.id)
    
    if user['is_banned']:
        await callback.answer("❌ Аккаунт заблокирован!", show_alert=True)
        return
    
    if user['key_issued']:
        # Показать существующий ключ
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT key_value FROM issued_keys WHERE user_id = ?",
                (callback.from_user.id,)
            ) as cursor:
                key = await cursor.fetchone()
                if key:
                    await callback.answer("🔑 Ваш ключ:", show_alert=True)
                    await callback.message.answer(
                        f"🔑 <b>Ваш ключ активации:</b>\n\n"
                        f"<code>{key[0]}</code>\n\n"
                        f"<i>Скопируй его и вставь в программу!</i>\n\n"
                        f"📥 Скачать чит: {WEBAPP_URL}",
                        parse_mode="HTML"
                    )
                    return
    
    if not user['is_completed']:
        remaining = REQUIRED_VIDEOS - user['video_count']
        await callback.answer(
            f"❌ Выполните задание! Осталось: {remaining} видео",
            show_alert=True
        )
        return
    
    # Выдаем ключ
    key = await issue_key(callback.from_user.id)
    
    if key:
        await callback.answer("🎉 Ключ выдан!", show_alert=True)
        await callback.message.answer(
            f"🎉 <b>Поздравляем! Вы получили ключ!</b>\n\n"
            f"🔑 <b>Ваш ключ активации:</b>\n"
            f"<code>{key}</code>\n\n"
            f"📥 <b>Скачать чит:</b>\n"
            f"{WEBAPP_URL}\n\n"
            f"<i>Сохрани ключ, он понадобится при активации!</i>",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "❌ Ошибка при выдаче ключа. Обратитесь к администратору."
        )


# ================== FASTAPI ROUTES ==================
def validate_init_data(init_data: str) -> dict | None:
    """Валидация данных от Telegram Mini App"""
    try:
        parsed = parse_qs(init_data)
        check_hash = parsed.get("hash", [None])[0]
        if not check_hash:
            return None

        data_check_arr = []
        for key, val in sorted(parsed.items()):
            if key != "hash":
                data_check_arr.append(f"{key}={val[0]}")
        data_check_string = "\n".join(data_check_arr)

        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if computed_hash == check_hash:
            user_data = parsed.get("user", [None])[0]
            if user_data:
                return json.loads(unquote(user_data))
        return None
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return None


@app.get("/api/user/{user_id}")
async def api_user(user_id: int):
    try:
        data = await get_user_data(user_id)
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(500, str(e))


@app.get("/api/stats")
async def api_stats():
    try:
        data = await get_stats()
        return JSONResponse(data)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/leaderboard")
async def api_leaderboard():
    try:
        data = await get_leaderboard()
        return JSONResponse(data)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/validate")
async def api_validate(request: Request):
    body = await request.json()
    init_data = body.get("initData", "")
    user = validate_init_data(init_data)
    if user:
        return JSONResponse({"valid": True, "user": user})
    return JSONResponse({"valid": False})


# ================== HTML FRONTEND ==================
HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1.0">
    <title>AimNoob | Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
        }}
        
        .card {{
            background: rgba(26, 26, 46, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(108, 92, 231, 0.3);
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            overflow: hidden;
            margin: 15px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #6c5ce7, #a29bfe);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .nav-tabs {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            overflow-x: auto;
        }}
        
        .tab {{
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            cursor: pointer;
            white-space: nowrap;
        }}
        
        .tab.active {{
            background: #6c5ce7;
        }}
        
        .section {{
            display: none;
        }}
        
        .section.active {{
            display: block;
        }}
        
        .video-item {{
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 8px;
        }}
        
        .copy-block {{
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 12px;
            margin: 10px 0;
            cursor: pointer;
        }}
        
        .key-value {{
            background: rgba(0,0,0,0.5);
            padding: 15px;
            border-radius: 10px;
            font-family: monospace;
            font-size: 18px;
            text-align: center;
            cursor: pointer;
            margin: 15px 0;
        }}
        
        .btn {{
            background: linear-gradient(135deg, #6c5ce7, #a29bfe);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
        }}
        
        .btn-success {{
            background: linear-gradient(135deg, #00e676, #00c853);
        }}
        
        .toast {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #6c5ce7;
            padding: 10px 20px;
            border-radius: 10px;
            display: none;
            z-index: 1000;
        }}
        
        h3 {{
            margin-bottom: 10px;
            font-size: 18px;
        }}
        
        a {{
            color: #6c5ce7;
            text-decoration: none;
        }}
        
        .status-emoji {{
            font-size: 48px;
            text-align: center;
            margin-bottom: 10px;
        }}
        
        .status-title {{
            text-align: center;
            font-size: 20px;
            margin-bottom: 5px;
        }}
        
        .status-text {{
            text-align: center;
            opacity: 0.8;
            font-size: 14px;
        }}
        
        .warning {{
            background: rgba(255, 107, 107, 0.2);
            border: 1px solid rgba(255, 107, 107, 0.3);
            padding: 10px;
            border-radius: 10px;
            margin-top: 10px;
            font-size: 12px;
        }}
        
        .step {{
            margin-bottom: 15px;
        }}
        
        .step-number {{
            display: inline-block;
            width: 24px;
            height: 24px;
            background: #6c5ce7;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-size: 12px;
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card" id="statusCard">
            <div class="status-emoji" id="statusEmoji">🎮</div>
            <div class="status-title" id="statusTitle">Добро пожаловать!</div>
            <div class="status-text" id="statusText">Выполни задание и получи ключ</div>
        </div>
        
        <div class="card">
            <h3>📊 Прогресс задания</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0/{REQUIRED_VIDEOS}</div>
            </div>
            <div id="progressText" style="text-align: center; margin-top: 10px;">0 из {REQUIRED_VIDEOS} видео</div>
        </div>
        
        <div class="nav-tabs">
            <div class="tab active" onclick="switchTab('task')">📋 Задание</div>
            <div class="tab" onclick="switchTab('data')">📝 Данные</div>
            <div class="tab" onclick="switchTab('videos')">📹 Мои видео</div>
            <div class="tab" onclick="switchTab('key')">🔑 Ключ</div>
            <div class="tab" onclick="switchTab('top')">🏆 Топ</div>
        </div>
        
        <div id="taskSection" class="section active">
            <div class="card">
                <h3>📋 Инструкция</h3>
                
                <div class="step">
                    <span class="step-number">1</span>
                    <strong>Найди видео</strong><br>
                    Берёшь видео с TikTok из Telegram-каналов. Тематика: чит Standoff 2 0.37.1. Видео должны быть <b>БЕЗ</b> водяных знаков.
                </div>
                
                <div class="step">
                    <span class="step-number">2</span>
                    <strong>Выложи на YouTube</strong><br>
                    Загружаешь как <b>обычный</b> ролик (НЕ Shorts). Вставляешь название и описание из раздела «Данные». В комментариях — ссылку на ТГ-канал.
                </div>
                
                <div class="step">
                    <span class="step-number">3</span>
                    <strong>Отправь ссылку</strong><br>
                    Отправь ссылку на загруженное видео боту. Повтори {REQUIRED_VIDEOS} раз. После проверки — получишь ключ!
                </div>
                
                <div class="warning">
                    ⚠️ Без ссылки в комментариях на ТГ-канал выдачи не будет! Это обязательное условие.
                </div>
                
                <button class="btn" onclick="openBot()">📤 Отправить ссылку боту</button>
            </div>
        </div>
        
        <div id="dataSection" class="section">
            <div class="card">
                <h3>📝 Название видео</h3>
                <div class="copy-block" onclick="copyText('{VIDEO_TITLE}')">
                    {VIDEO_TITLE}
                </div>
                
                <h3>📄 Описание</h3>
                <div class="copy-block" onclick="copyText(`{VIDEO_DESCRIPTION}`)">
                    {VIDEO_DESCRIPTION[:150]}...
                </div>
                
                <h3>💬 Комментарий</h3>
                <div class="copy-block" onclick="copyText('{COMMENT_TEXT}')">
                    {COMMENT_TEXT}
                </div>
                
                <div class="warning">
                    💡 Нажми на блок чтобы скопировать текст
                </div>
            </div>
        </div>
        
        <div id="videosSection" class="section">
            <div class="card">
                <h3>📹 Мои видео</h3>
                <div id="videosList">
                    <div style="text-align: center;">Загрузка...</div>
                </div>
            </div>
        </div>
        
        <div id="keySection" class="section">
            <div class="card" id="keyContent">
                <div style="text-align: center;">Загрузка...</div>
            </div>
        </div>
        
        <div id="topSection" class="section">
            <div class="card">
                <h3>🏆 Таблица лидеров</h3>
                <div id="leaderboardList">
                    <div style="text-align: center;">Загрузка...</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="toast" id="toast">✅ Скопировано!</div>
    
    <script>
        const REQUIRED = {REQUIRED_VIDEOS};
        let userData = null;
        let userId = null;
        
        const tg = window.Telegram?.WebApp;
        if (tg) {{
            tg.ready();
            tg.expand();
            if (tg.initDataUnsafe?.user) {{
                userId = tg.initDataUnsafe.user.id;
                const name = tg.initDataUnsafe.user.first_name || 'User';
                document.title = `AimNoob | ${{name}}`;
            }}
        }}
        
        if (!userId) {{
            const params = new URLSearchParams(window.location.search);
            userId = params.get('user_id');
        }}
        
        async function loadUserData() {{
            if (!userId) return;
            try {{
                const res = await fetch(`/api/user/${{userId}}`);
                userData = await res.json();
                renderAll();
            }} catch(e) {{
                console.error(e);
            }}
        }}
        
        async function loadLeaderboard() {{
            try {{
                const res = await fetch('/api/leaderboard');
                const data = await res.json();
                renderLeaderboard(data);
            }} catch(e) {{
                console.error(e);
            }}
        }}
        
        function renderAll() {{
            if (!userData) return;
            
            const count = userData.video_count || 0;
            const percent = (count / REQUIRED) * 100;
            document.getElementById('progressFill').style.width = `${{percent}}%`;
            document.getElementById('progressFill').textContent = `${{count}}/${{REQUIRED}}`;
            document.getElementById('progressText').textContent = `${{count}} из ${{REQUIRED}} видео`;
            
            if (userData.is_banned) {{
                document.getElementById('statusEmoji').textContent = '🚫';
                document.getElementById('statusTitle').textContent = 'Аккаунт заблокирован';
                document.getElementById('statusText').textContent = 'Обратитесь к администратору';
            }} else if (userData.key_issued && userData.key) {{
                document.getElementById('statusEmoji').textContent = '🎉';
                document.getElementById('statusTitle').textContent = 'Ключ получен!';
                document.getElementById('statusText').textContent = 'Скачай чит и активируй';
            }} else if (userData.is_completed) {{
                document.getElementById('statusEmoji').textContent = '✅';
                document.getElementById('statusTitle').textContent = 'Задание выполнено!';
                document.getElementById('statusText').textContent = 'Ожидай проверки администратором';
            }} else if (count > 0) {{
                document.getElementById('statusEmoji').textContent = '⏳';
                document.getElementById('statusTitle').textContent = 'В процессе';
                document.getElementById('statusText').textContent = `Осталось ${{REQUIRED - count}} видео`;
            }} else {{
                document.getElementById('statusEmoji').textContent = '🎮';
                document.getElementById('statusTitle').textContent = 'Добро пожаловать!';
                document.getElementById('statusText').textContent = 'Выполни задание и получи чит';
            }}
            
            renderVideos();
            renderKey();
        }}
        
        function renderVideos() {{
            const container = document.getElementById('videosList');
            const videos = userData?.videos || [];
            
            if (videos.length === 0) {{
                container.innerHTML = '<div style="text-align: center;">📭 Видео пока нет</div>';
                return;
            }}
            
            let html = '';
            videos.forEach((v, i) => {{
                const statusColor = v.status === 'approved' ? '#00e676' : v.status === 'rejected' ? '#ff5252' : '#ffab40';
                const statusText = v.status === 'approved' ? '✅ Принято' : v.status === 'rejected' ? '❌ Отклонено' : '⏳ На проверке';
                const date = v.submitted_at ? new Date(v.submitted_at).toLocaleDateString('ru-RU') : '';
                html += `
                    <div class="video-item">
                        <div><b>#${{i+1}}</b></div>
                        <div style="flex:1; margin: 0 10px;">
                            <a href="${{v.video_url}}" target="_blank" style="color: #6c5ce7;">Ссылка</a>
                            <div style="font-size: 11px; color: #888;">${{date}}</div>
                        </div>
                        <div style="color: ${{statusColor}};">${{statusText}}</div>
                    </div>
                `;
            }});
            container.innerHTML = html;
        }}
        
        function renderKey() {{
            const container = document.getElementById('keyContent');
            
            if (userData?.key) {{
                container.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 48px;">🔑</div>
                        <h3>Ваш ключ активации</h3>
                        <div class="key-value" onclick="copyKey()">${{userData.key}}</div>
                        <button class="btn btn-success" onclick="window.open('{DOWNLOAD_LINK}', '_blank')">📥 Скачать чит</button>
                        <button class="btn" onclick="window.open('{CHANNEL_LINK}', '_blank')">📌 Наш канал</button>
                        <div class="warning" style="margin-top: 15px;">
                            ⚠️ Ключ одноразовый — никому не передавай!
                        </div>
                    </div>
                `;
            }} else if (userData?.is_completed) {{
                container.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 48px;">⏳</div>
                        <h3>Ожидание проверки</h3>
                        <p>Все видео отправлены! Администратор проверит и выдаст ключ. Обычно это занимает до 24 часов.</p>
                    </div>
                `;
            }} else {{
                const left = REQUIRED - (userData?.video_count || 0);
                container.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 48px;">🔒</div>
                        <h3>Ключ пока недоступен</h3>
                        <p>Осталось отправить <b>${{left}}</b> видео. Выполни задание полностью!</p>
                        <button class="btn" onclick="openBot()">📤 Продолжить задание</button>
                    </div>
                `;
            }}
        }}
        
        function renderLeaderboard(data) {{
            const container = document.getElementById('leaderboardList');
            
            if (!data || data.length === 0) {{
                container.innerHTML = '<div style="text-align: center;">🏆 Пока никто не отправлял видео</div>';
                return;
            }}
            
            const medals = ['🥇', '🥈', '🥉'];
            let html = '';
            
            data.forEach((user, i) => {{
                const medal = medals[i] || `#${{i+1}}`;
                const isMe = user.user_id == userId;
                let badge = '';
                if (user.key_issued) badge = ' 🔑';
                else if (user.is_completed) badge = ' ✅';
                
                html += `
                    <div class="video-item" style="${{isMe ? 'border-left: 3px solid #6c5ce7;' : ''}}">
                        <div style="font-size: 20px;">${{medal}}</div>
                        <div style="flex:1;">
                            <div><b>${{user.full_name || 'User'}}${{isMe ? ' 👈' : ''}}</b></div>
                            <div style="font-size: 11px; color: #888;">@${{user.username || '—'}}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: bold;">${{user.video_count}}/${{REQUIRED}}</div>
                            <div style="font-size: 11px;">${{badge}}</div>
                        </div>
                    </div>
                `;
            }});
            
            container.innerHTML = html;
        }}
        
        function switchTab(tab) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            
            if (tab === 'task') {{
                document.querySelectorAll('.tab')[0].classList.add('active');
                document.getElementById('taskSection').classList.add('active');
            }} else if (tab === 'data') {{
                document.querySelectorAll('.tab')[1].classList.add('active');
                document.getElementById('dataSection').classList.add('active');
            }} else if (tab === 'videos') {{
                document.querySelectorAll('.tab')[2].classList.add('active');
                document.getElementById('videosSection').classList.add('active');
            }} else if (tab === 'key') {{
                document.querySelectorAll('.tab')[3].classList.add('active');
                document.getElementById('keySection').classList.add('active');
            }} else if (tab === 'top') {{
                document.querySelectorAll('.tab')[4].classList.add('active');
                document.getElementById('topSection').classList.add('active');
                loadLeaderboard();
            }}
        }}
        
        function copyText(text) {{
            navigator.clipboard.writeText(text);
            showToast('✅ Скопировано!');
        }}
        
        function copyKey() {{
            if (userData?.key) {{
                navigator.clipboard.writeText(userData.key);
                showToast('🔑 Ключ скопирован!');
            }}
        }}
        
        function showToast(msg) {{
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.style.display = 'block';
            setTimeout(() => {{
                toast.style.display = 'none';
            }}, 2000);
        }}
        
        function openBot() {{
            if (tg) {{
                tg.close();
            }} else {{
                window.open('https://t.me/AimNooBBot', '_blank');
            }}
        }}
        
        loadUserData();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML_TEMPLATE)


@app.get("/app", response_class=HTMLResponse)
async def app_page():
    return HTMLResponse(content=HTML_TEMPLATE)


@app.get("/health")
async def health():
    return {"status": "ok", "domain": DOMAIN}


# ================== ЗАПУСК ==================
async def run_bot():
    """Запуск Telegram бота"""
    await init_db()
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot, skip_updates=True)


def run_fastapi():
    """Запуск FastAPI сервера"""
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")


if __name__ == "__main__":
    logger.info("Starting AimNoob application...")
    
    # Запускаем FastAPI в отдельном потоке
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    
    # Запускаем бота в главном потоке
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
