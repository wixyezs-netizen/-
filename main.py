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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1.0">
    <title>AimNoob | Premium Cheat</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #8b5cf6;
            --primary-dark: #7c3aed;
            --primary-light: #a78bfa;
            --secondary: #06b6d4;
            --accent: #f59e0b;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --dark: #0f0f1a;
            --darker: #080810;
            --card: rgba(15, 15, 26, 0.8);
            --card-border: rgba(139, 92, 246, 0.2);
            --text: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.6);
            --glow: 0 0 40px rgba(139, 92, 246, 0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--darker);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }

        /* Animated Background */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
        }

        .bg-animation::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(6, 182, 212, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(245, 158, 11, 0.08) 0%, transparent 40%);
            animation: bgRotate 30s linear infinite;
        }

        @keyframes bgRotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .floating-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(60px);
            opacity: 0.5;
            animation: float 20s ease-in-out infinite;
        }

        .orb-1 {
            width: 300px;
            height: 300px;
            background: var(--primary);
            top: 10%;
            left: -10%;
            animation-delay: 0s;
        }

        .orb-2 {
            width: 200px;
            height: 200px;
            background: var(--secondary);
            bottom: 20%;
            right: -5%;
            animation-delay: -7s;
        }

        .orb-3 {
            width: 150px;
            height: 150px;
            background: var(--accent);
            top: 50%;
            left: 50%;
            animation-delay: -14s;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0) translateX(0); }
            25% { transform: translateY(-30px) translateX(20px); }
            50% { transform: translateY(20px) translateX(-20px); }
            75% { transform: translateY(-10px) translateX(30px); }
        }

        /* Grid Pattern */
        .grid-pattern {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(rgba(139, 92, 246, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(139, 92, 246, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            z-index: -1;
        }

        /* Container */
        .container {
            max-width: 480px;
            margin: 0 auto;
            padding: 16px;
            padding-bottom: 100px;
        }

        /* Header */
        .header {
            text-align: center;
            padding: 24px 0;
            margin-bottom: 20px;
        }

        .logo {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .logo-icon {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: var(--glow);
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); box-shadow: var(--glow); }
            50% { transform: scale(1.05); box-shadow: 0 0 60px rgba(139, 92, 246, 0.5); }
        }

        .logo-text {
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, var(--primary-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -1px;
        }

        .header-subtitle {
            color: var(--text-secondary);
            font-size: 14px;
            font-weight: 500;
        }

        /* Status Card */
        .status-card {
            background: var(--card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 16px;
            position: relative;
            overflow: hidden;
        }

        .status-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--secondary), var(--accent));
        }

        .status-card.success::before {
            background: linear-gradient(90deg, var(--success), #34d399);
        }

        .status-card.warning::before {
            background: linear-gradient(90deg, var(--warning), #fbbf24);
        }

        .status-card.danger::before {
            background: linear-gradient(90deg, var(--danger), #f87171);
        }

        .status-content {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .status-icon {
            width: 64px;
            height: 64px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.1));
            flex-shrink: 0;
        }

        .status-info {
            flex: 1;
        }

        .status-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .status-text {
            color: var(--text-secondary);
            font-size: 13px;
            line-height: 1.4;
        }

        /* Progress Section */
        .progress-card {
            background: var(--card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 20px;
            margin-bottom: 16px;
        }

        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .progress-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .progress-value {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .progress-bar-container {
            position: relative;
            height: 12px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 6px;
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .progress-bar-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.3),
                transparent
            );
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .progress-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 16px;
        }

        .stat-item {
            text-align: center;
            padding: 12px 8px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
        }

        .stat-value {
            font-size: 20px;
            font-weight: 700;
            color: var(--primary-light);
        }

        .stat-label {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Navigation */
        .nav-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(15, 15, 26, 0.95);
            backdrop-filter: blur(20px);
            border-top: 1px solid var(--card-border);
            padding: 12px 16px;
            padding-bottom: max(12px, env(safe-area-inset-bottom));
            z-index: 100;
        }

        .nav-tabs {
            display: flex;
            justify-content: space-around;
            max-width: 480px;
            margin: 0 auto;
        }

        .nav-tab {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: 8px 16px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: var(--text-secondary);
            background: transparent;
            border: none;
            font-family: inherit;
        }

        .nav-tab:active {
            transform: scale(0.95);
        }

        .nav-tab.active {
            color: var(--primary);
            background: rgba(139, 92, 246, 0.15);
        }

        .nav-tab-icon {
            font-size: 22px;
            line-height: 1;
        }

        .nav-tab-label {
            font-size: 10px;
            font-weight: 600;
        }

        /* Sections */
        .section {
            display: none;
            animation: fadeIn 0.3s ease;
        }

        .section.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Cards */
        .card {
            background: var(--card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }

        .card:hover {
            border-color: rgba(139, 92, 246, 0.4);
        }

        .card-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 16px;
        }

        .card-title-icon {
            font-size: 20px;
        }

        /* Steps */
        .steps {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .step {
            display: flex;
            gap: 14px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
        }

        .step:hover {
            background: rgba(139, 92, 246, 0.05);
            border-color: rgba(139, 92, 246, 0.2);
        }

        .step-number {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 700;
            flex-shrink: 0;
        }

        .step-content h4 {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .step-content p {
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.5;
        }

        /* Buttons */
        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 16px 24px;
            border: none;
            border-radius: 14px;
            font-family: inherit;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            box-shadow: 0 4px 20px rgba(139, 92, 246, 0.4);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(139, 92, 246, 0.5);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .btn-success {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
            box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
        }

        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(16, 185, 129, 0.5);
        }

        .btn-outline {
            background: transparent;
            border: 2px solid var(--card-border);
            color: var(--text);
        }

        .btn-outline:hover {
            border-color: var(--primary);
            background: rgba(139, 92, 246, 0.1);
        }

        .btn-icon {
            font-size: 18px;
        }

        /* Copy Blocks */
        .copy-section {
            margin-bottom: 20px;
        }

        .copy-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .copy-block {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .copy-block:hover {
            background: rgba(139, 92, 246, 0.1);
            border-color: var(--primary);
        }

        .copy-block:active {
            transform: scale(0.98);
        }

        .copy-block-text {
            font-size: 13px;
            line-height: 1.6;
            color: var(--text);
            white-space: pre-wrap;
            word-break: break-word;
        }

        .copy-hint {
            position: absolute;
            top: 8px;
            right: 8px;
            font-size: 10px;
            color: var(--text-secondary);
            background: rgba(0, 0, 0, 0.3);
            padding: 4px 8px;
            border-radius: 6px;
        }

        /* Video List */
        .video-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .video-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
        }

        .video-item:hover {
            background: rgba(139, 92, 246, 0.05);
        }

        .video-number {
            width: 28px;
            height: 28px;
            background: rgba(139, 92, 246, 0.2);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            color: var(--primary-light);
            flex-shrink: 0;
        }

        .video-info {
            flex: 1;
            min-width: 0;
        }

        .video-link {
            color: var(--primary-light);
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .video-date {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .video-status {
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            flex-shrink: 0;
        }

        .video-status.pending {
            background: rgba(245, 158, 11, 0.15);
            color: var(--warning);
        }

        .video-status.approved {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }

        .video-status.rejected {
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger);
        }

        /* Key Display */
        .key-container {
            text-align: center;
            padding: 20px 0;
        }

        .key-icon {
            font-size: 64px;
            margin-bottom: 16px;
            animation: bounce 2s ease-in-out infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .key-box {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.1));
            border: 2px solid var(--primary);
            border-radius: 16px;
            padding: 20px;
            margin: 20px 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .key-box:hover {
            transform: scale(1.02);
            box-shadow: var(--glow);
        }

        .key-box:active {
            transform: scale(0.98);
        }

        .key-value {
            font-family: 'Courier New', monospace;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 2px;
            color: var(--primary-light);
        }

        .key-hint {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 8px;
        }

        /* Leaderboard */
        .leaderboard-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .leaderboard-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
        }

        .leaderboard-item.is-me {
            background: rgba(139, 92, 246, 0.1);
            border-color: var(--primary);
        }

        .leaderboard-item.top-3 {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.05));
            border-color: rgba(245, 158, 11, 0.3);
        }

        .leaderboard-rank {
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }

        .leaderboard-rank.number {
            font-size: 14px;
            font-weight: 700;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }

        .leaderboard-user {
            flex: 1;
            min-width: 0;
        }

        .leaderboard-name {
            font-size: 14px;
            font-weight: 600;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .leaderboard-username {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .leaderboard-score {
            text-align: right;
            flex-shrink: 0;
        }

        .leaderboard-videos {
            font-size: 16px;
            font-weight: 700;
            color: var(--primary-light);
        }

        .leaderboard-badge {
            font-size: 16px;
            margin-top: 2px;
        }

        /* Alert Box */
        .alert {
            padding: 14px 16px;
            border-radius: 12px;
            font-size: 13px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-top: 16px;
        }

        .alert-warning {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #fcd34d;
        }

        .alert-icon {
            font-size: 16px;
            flex-shrink: 0;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
        }

        .empty-icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }

        .empty-text {
            color: var(--text-secondary);
            font-size: 14px;
        }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: var(--primary);
            color: white;
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            opacity: 0;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }

        /* Loading */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(139, 92, 246, 0.2);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 4px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 2px;
        }

        /* Responsive */
        @media (max-width: 380px) {
            .container {
                padding: 12px;
            }
            
            .logo-text {
                font-size: 26px;
            }
            
            .progress-value {
                font-size: 20px;
            }
        }
    </style>
</head>
<body>
    <!-- Animated Background -->
    <div class="bg-animation">
        <div class="floating-orb orb-1"></div>
        <div class="floating-orb orb-2"></div>
        <div class="floating-orb orb-3"></div>
    </div>
    <div class="grid-pattern"></div>

    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon">🎯</div>
                <span class="logo-text">AimNoob</span>
            </div>
            <div class="header-subtitle">Premium Cheat for Standoff 2</div>
        </header>

        <!-- Status Card -->
        <div class="status-card" id="statusCard">
            <div class="status-content">
                <div class="status-icon" id="statusIcon">🎮</div>
                <div class="status-info">
                    <div class="status-title" id="statusTitle">Загрузка...</div>
                    <div class="status-text" id="statusText">Получение данных</div>
                </div>
            </div>
        </div>

        <!-- Progress Card -->
        <div class="progress-card">
            <div class="progress-header">
                <span class="progress-title">ПРОГРЕСС ЗАДАНИЯ</span>
                <span class="progress-value" id="progressValue">0/""" + str(REQUIRED_VIDEOS) + """</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" id="progressFill" style="width: 0%"></div>
            </div>
            <div class="progress-stats">
                <div class="stat-item">
                    <div class="stat-value" id="statSent">0</div>
                    <div class="stat-label">Отправлено</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="statPending">0</div>
                    <div class="stat-label">На проверке</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="statApproved">0</div>
                    <div class="stat-label">Принято</div>
                </div>
            </div>
        </div>

        <!-- Sections -->
        <div id="taskSection" class="section active">
            <div class="card">
                <div class="card-title">
                    <span class="card-title-icon">📋</span>
                    Как получить ключ
                </div>
                <div class="steps">
                    <div class="step">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <h4>Найди видео</h4>
                            <p>Скачай видео из TikTok или Telegram каналов на тему чита Standoff 2. Видео должны быть БЕЗ водяных знаков.</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-number">2</div>
                        <div class="step-content">
                            <h4>Загрузи на YouTube</h4>
                            <p>Выложи как обычное видео (НЕ Shorts). Используй название и описание из раздела «Данные».</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-number">3</div>
                        <div class="step-content">
                            <h4>Отправь ссылку</h4>
                            <p>Скопируй ссылку на видео и отправь боту. Повтори """ + str(REQUIRED_VIDEOS) + """ раз и получи ключ!</p>
                        </div>
                    </div>
                </div>
                
                <div class="alert alert-warning">
                    <span class="alert-icon">⚠️</span>
                    <span>В комментариях к видео обязательно оставь ссылку на наш Telegram канал!</span>
                </div>
                
                <button class="btn btn-primary" onclick="openBot()" style="margin-top: 20px;">
                    <span class="btn-icon">📤</span>
                    Отправить видео боту
                </button>
            </div>
        </div>

        <div id="dataSection" class="section">
            <div class="card">
                <div class="card-title">
                    <span class="card-title-icon">📝</span>
                    Данные для видео
                </div>
                
                <div class="copy-section">
                    <div class="copy-label">
                        <span>🎬</span> Название видео
                    </div>
                    <div class="copy-block" onclick="copyText(videoTitle, this)">
                        <div class="copy-block-text" id="videoTitleText"></div>
                        <span class="copy-hint">Нажми чтобы скопировать</span>
                    </div>
                </div>
                
                <div class="copy-section">
                    <div class="copy-label">
                        <span>📄</span> Описание
                    </div>
                    <div class="copy-block" onclick="copyText(videoDescription, this)">
                        <div class="copy-block-text" id="videoDescText"></div>
                        <span class="copy-hint">Нажми чтобы скопировать</span>
                    </div>
                </div>
                
                <div class="copy-section">
                    <div class="copy-label">
                        <span>💬</span> Комментарий
                    </div>
                    <div class="copy-block" onclick="copyText(commentText, this)">
                        <div class="copy-block-text" id="commentTextEl"></div>
                        <span class="copy-hint">Нажми чтобы скопировать</span>
                    </div>
                </div>
                
                <div class="copy-section">
                    <div class="copy-label">
                        <span>🏷️</span> Теги
                    </div>
                    <div class="copy-block" onclick="copyText(tagsText, this)">
                        <div class="copy-block-text" id="tagsTextEl"></div>
                        <span class="copy-hint">Нажми чтобы скопировать</span>
                    </div>
                </div>
            </div>
        </div>

        <div id="videosSection" class="section">
            <div class="card">
                <div class="card-title">
                    <span class="card-title-icon">📹</span>
                    Мои видео
                </div>
                <div id="videosList" class="video-list">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>

        <div id="keySection" class="section">
            <div class="card" id="keyContent">
                <div class="loading"><div class="spinner"></div></div>
            </div>
        </div>

        <div id="topSection" class="section">
            <div class="card">
                <div class="card-title">
                    <span class="card-title-icon">🏆</span>
                    Таблица лидеров
                </div>
                <div id="leaderboardList" class="leaderboard-list">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bottom Navigation -->
    <nav class="nav-container">
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('task')">
                <span class="nav-tab-icon">📋</span>
                <span class="nav-tab-label">Задание</span>
            </button>
            <button class="nav-tab" onclick="switchTab('data')">
                <span class="nav-tab-icon">📝</span>
                <span class="nav-tab-label">Данные</span>
            </button>
            <button class="nav-tab" onclick="switchTab('videos')">
                <span class="nav-tab-icon">📹</span>
                <span class="nav-tab-label">Видео</span>
            </button>
            <button class="nav-tab" onclick="switchTab('key')">
                <span class="nav-tab-icon">🔑</span>
                <span class="nav-tab-label">Ключ</span>
            </button>
            <button class="nav-tab" onclick="switchTab('top')">
                <span class="nav-tab-icon">🏆</span>
                <span class="nav-tab-label">Топ</span>
            </button>
        </div>
    </nav>

    <!-- Toast -->
    <div class="toast" id="toast">
        <span id="toastIcon">✅</span>
        <span id="toastText">Скопировано!</span>
    </div>

    <script>
        // Constants
        const REQUIRED = """ + str(REQUIRED_VIDEOS) + """;
        const CHANNEL_LINK = '""" + CHANNEL_LINK + """';
        const DOWNLOAD_LINK = '""" + DOWNLOAD_LINK + """';
        
        // Video data
        const videoTitle = `""" + VIDEO_TITLE + """`;
        const videoDescription = `""" + VIDEO_DESCRIPTION + """`;
        const commentText = `""" + COMMENT_TEXT + """`;
        const tagsText = `""" + TAGS + """`;
        
        // State
        let userData = null;
        let userId = null;
        
        // Telegram WebApp
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.ready();
            tg.expand();
            tg.setHeaderColor('#080810');
            tg.setBackgroundColor('#080810');
            
            if (tg.initDataUnsafe?.user) {
                userId = tg.initDataUnsafe.user.id;
            }
        }
        
        // Fallback for testing
        if (!userId) {
            const params = new URLSearchParams(window.location.search);
            userId = params.get('user_id');
        }
        
        // Initialize text content
        document.getElementById('videoTitleText').textContent = videoTitle;
        document.getElementById('videoDescText').textContent = videoDescription.substring(0, 200) + '...';
        document.getElementById('commentTextEl').textContent = commentText;
        document.getElementById('tagsTextEl').textContent = tagsText.substring(0, 100) + '...';
        
        // Load user data
        async function loadUserData() {
            if (!userId) {
                updateStatus('error', '❌', 'Ошибка авторизации', 'Откройте приложение через Telegram бота');
                return;
            }
            
            try {
                const res = await fetch(`/api/user/${userId}`);
                userData = await res.json();
                renderAll();
            } catch (e) {
                console.error(e);
                updateStatus('error', '❌', 'Ошибка загрузки', 'Не удалось получить данные');
            }
        }
        
        // Load leaderboard
        async function loadLeaderboard() {
            try {
                const res = await fetch('/api/leaderboard');
                const data = await res.json();
                renderLeaderboard(data);
            } catch (e) {
                console.error(e);
                document.getElementById('leaderboardList').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">❌</div>
                        <div class="empty-text">Не удалось загрузить данные</div>
                    </div>
                `;
            }
        }
        
        // Update status card
        function updateStatus(type, icon, title, text) {
            const card = document.getElementById('statusCard');
            const iconEl = document.getElementById('statusIcon');
            const titleEl = document.getElementById('statusTitle');
            const textEl = document.getElementById('statusText');
            
            card.className = 'status-card ' + type;
            iconEl.textContent = icon;
            titleEl.textContent = title;
            textEl.textContent = text;
        }
        
        // Render all
        function renderAll() {
            if (!userData) return;
            
            const count = userData.video_count || 0;
            const percent = Math.min((count / REQUIRED) * 100, 100);
            
            // Progress
            document.getElementById('progressFill').style.width = `${percent}%`;
            document.getElementById('progressValue').textContent = `${count}/${REQUIRED}`;
            
            // Stats
            const videos = userData.videos || [];
            const pending = videos.filter(v => v.status === 'pending').length;
            const approved = videos.filter(v => v.status === 'approved').length;
            
            document.getElementById('statSent').textContent = count;
            document.getElementById('statPending').textContent = pending;
            document.getElementById('statApproved').textContent = approved;
            
            // Status
            if (userData.is_banned) {
                updateStatus('danger', '🚫', 'Аккаунт заблокирован', 'Обратитесь к администратору для разблокировки');
            } else if (userData.key_issued && userData.key) {
                updateStatus('success', '🎉', 'Ключ получен!', 'Скачай чит и активируй его с помощью ключа');
            } else if (userData.is_completed) {
                updateStatus('warning', '⏳', 'Ожидание проверки', 'Все видео отправлены. Администратор скоро проверит');
            } else if (count > 0) {
                updateStatus('', '🔥', 'Продолжай работать!', `Осталось отправить ${REQUIRED - count} видео`);
            } else {
                updateStatus('', '🎮', 'Добро пожаловать!', 'Выполни задание и получи доступ к читу');
            }
            
            renderVideos();
            renderKey();
        }
        
        // Render videos
        function renderVideos() {
            const container = document.getElementById('videosList');
            const videos = userData?.videos || [];
            
            if (videos.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">📭</div>
                        <div class="empty-text">Вы еще не отправили ни одного видео</div>
                    </div>
                `;
                return;
            }
            
            let html = '';
            videos.forEach((v, i) => {
                const statusClass = v.status === 'approved' ? 'approved' : v.status === 'rejected' ? 'rejected' : 'pending';
                const statusText = v.status === 'approved' ? '✓ Принято' : v.status === 'rejected' ? '✗ Отклонено' : '⏳ Проверка';
                const date = v.submitted_at ? new Date(v.submitted_at).toLocaleDateString('ru-RU') : '';
                
                html += `
                    <div class="video-item">
                        <div class="video-number">${i + 1}</div>
                        <div class="video-info">
                            <a href="${v.video_url}" target="_blank" class="video-link">${v.video_url}</a>
                            <div class="video-date">${date}</div>
                        </div>
                        <div class="video-status ${statusClass}">${statusText}</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        // Render key
        function renderKey() {
            const container = document.getElementById('keyContent');
            
            if (userData?.key) {
                container.innerHTML = `
                    <div class="key-container">
                        <div class="key-icon">🔑</div>
                        <h3 style="font-size: 20px; margin-bottom: 8px;">Ваш ключ активации</h3>
                        <p style="color: var(--text-secondary); font-size: 14px;">Нажмите чтобы скопировать</p>
                        <div class="key-box" onclick="copyKey()">
                            <div class="key-value">${userData.key}</div>
                            <div class="key-hint">Tap to copy</div>
                        </div>
                        <button class="btn btn-success" onclick="window.open('${DOWNLOAD_LINK}', '_blank')">
                            <span class="btn-icon">📥</span>
                            Скачать AimNoob
                        </button>
                        <button class="btn btn-outline" onclick="window.open('${CHANNEL_LINK}', '_blank')" style="margin-top: 10px;">
                            <span class="btn-icon">📢</span>
                            Наш Telegram канал
                        </button>
                        <div class="alert alert-warning" style="margin-top: 16px;">
                            <span class="alert-icon">🔒</span>
                            <span>Ключ одноразовый — никому не передавай!</span>
                        </div>
                    </div>
                `;
            } else if (userData?.is_completed) {
                container.innerHTML = `
                    <div class="key-container">
                        <div class="key-icon">⏳</div>
                        <h3 style="font-size: 20px; margin-bottom: 8px;">Ожидание проверки</h3>
                        <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.6;">
                            Все видео успешно отправлены!<br>
                            Администратор проверит их и выдаст ключ.<br>
                            Обычно это занимает до 24 часов.
                        </p>
                        <button class="btn btn-outline" onclick="window.open('${CHANNEL_LINK}', '_blank')" style="margin-top: 20px;">
                            <span class="btn-icon">📢</span>
                            Следить за новостями
                        </button>
                    </div>
                `;
            } else {
                const remaining = REQUIRED - (userData?.video_count || 0);
                container.innerHTML = `
                    <div class="key-container">
                        <div class="key-icon">🔒</div>
                        <h3 style="font-size: 20px; margin-bottom: 8px;">Ключ пока недоступен</h3>
                        <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.6;">
                            Для получения ключа нужно отправить<br>
                            ещё <strong style="color: var(--primary-light);">${remaining}</strong> видео
                        </p>
                        <button class="btn btn-primary" onclick="openBot()" style="margin-top: 20px;">
                            <span class="btn-icon">📤</span>
                            Продолжить задание
                        </button>
                    </div>
                `;
            }
        }
        
        // Render leaderboard
        function renderLeaderboard(data) {
            const container = document.getElementById('leaderboardList');
            
            if (!data || data.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🏆</div>
                        <div class="empty-text">Пока никто не отправлял видео</div>
                    </div>
                `;
                return;
            }
            
            const medals = ['🥇', '🥈', '🥉'];
            let html = '';
            
            data.forEach((user, i) => {
                const isMe = user.user_id == userId;
                const isTop3 = i < 3;
                let badge = '';
                if (user.key_issued) badge = '🔑';
                else if (user.is_completed) badge = '✅';
                
                html += `
                    <div class="leaderboard-item ${isMe ? 'is-me' : ''} ${isTop3 ? 'top-3' : ''}">
                        <div class="leaderboard-rank ${!isTop3 ? 'number' : ''}">${isTop3 ? medals[i] : i + 1}</div>
                        <div class="leaderboard-user">
                            <div class="leaderboard-name">${user.full_name || 'User'}${isMe ? ' (Вы)' : ''}</div>
                            <div class="leaderboard-username">@${user.username || '—'}</div>
                        </div>
                        <div class="leaderboard-score">
                            <div class="leaderboard-videos">${user.video_count}/${REQUIRED}</div>
                            <div class="leaderboard-badge">${badge}</div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        // Switch tabs
        function switchTab(tab) {
            // Update nav
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            
            const tabs = ['task', 'data', 'videos', 'key', 'top'];
            const index = tabs.indexOf(tab);
            if (index >= 0) {
                document.querySelectorAll('.nav-tab')[index].classList.add('active');
                document.getElementById(`${tab}Section`).classList.add('active');
            }
            
            // Load leaderboard when switching to top
            if (tab === 'top') {
                loadLeaderboard();
            }
            
            // Haptic feedback
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.selectionChanged();
            }
        }
        
        // Copy text
        function copyText(text, element) {
            navigator.clipboard.writeText(text).then(() => {
                showToast('✅', 'Скопировано!');
                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('success');
                }
            }).catch(() => {
                showToast('❌', 'Ошибка копирования');
            });
        }
        
        // Copy key
        function copyKey() {
            if (userData?.key) {
                navigator.clipboard.writeText(userData.key).then(() => {
                    showToast('🔑', 'Ключ скопирован!');
                    if (tg?.HapticFeedback) {
                        tg.HapticFeedback.notificationOccurred('success');
                    }
                });
            }
        }
        
        // Show toast
        function showToast(icon, text) {
            const toast = document.getElementById('toast');
            const toastIcon = document.getElementById('toastIcon');
            const toastText = document.getElementById('toastText');
            
            toastIcon.textContent = icon;
            toastText.textContent = text;
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2000);
        }
        
        // Open bot
        function openBot() {
            if (tg) {
                tg.close();
            } else {
                window.open('https://t.me/AimNooBBot', '_blank');
            }
        }
        
        // Initialize
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
