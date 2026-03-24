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
DOWNLOAD_LINK = "https://t.me/AimNooBsoft"
WEBAPP_URL = f"https://{DOMAIN}"

# Данные для видео
VIDEO_TITLE = "⚡️КАК СКАЧАТЬ ЧИТ 0.37.1 STANDOFF 2 БЕЗ РУТ И БАНА ПОЛНАЯ УСТАНОВКА"

VIDEO_DESCRIPTION = """👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft


standoff 2, стандофф, standoff, стендофф, standoff2, веля, стендофф 2, стэндофф 2, стендоф, стэндофф, standof, стандофф2, стандоф, рик, обнова 0.37.1, обновление 0.37.1, kasai_standoff2, стандофф обновление, со2, so2, стандоф 2, стендофф2, 0.37.1 стандофф 2, стендов, стандофф 2 0.37.1, 0.37.1, в стандофф 2, standoff 2 0.37.1, ric, скрафтил аркану, крафт стандофф 2, мем стандофф, мем стандофф 2, девушка в стандофф 2, wonderfull shorts, софт касай, казашка, kazashka, мафиозник, kasai софт, kasai shorts, fragmovie standoff, фрагмуви стандофф, apollon standoff 2, apollon shorts, казашка стандофф 2, мафиозник и казашка, мемы стандофф 2, мемы стандофф 2 шортс, мемы стандофф 2 без мата, смешные моменты стандофф 2, стандофф 2 мемы шортс, юкан, шортс, казашка standoff 2, казашка стандофф, девушка играет в стандофф, shorts, крафт арканы standoff 2, standoff 2 full allies gameplay, лучший игрок на телефоне в стандофф 2, fragmovie standoff 2, мувик стандофф 2, ipad pro 2020 standoff 2, айфон 7 стандофф 2, ipad pro 2021 standoff 2, frontos, лучший игрок с телефона standoff 2, мувики стандофф 2, фрагмуви стандофф 2, standoff 2 fragmovie, #h9ije, айпад 9 стандофф 2, стандофф 2 фрагмуви, стандофф 2 мувик, h9nto, айпад 2021 стандофф 2, ipad pro 2018 standoff 2, best player standoff 2, en9rjee so2, h9ije standoff 2, m9 bayonet standoff 2, стендоф 2, обзор обновления 0.37.1, standoff 2 allies legend, standoff 2 allies gameplay, standoff 2 full competitive match gameplay, standoff 2 competitive gameplay, lilith so2, standoff 2 allies, standoff 2 ranked, standoff 2 settings, standoff 2 competitive, мувик, lilith so2 allies, девушка, сталофф, belka, веля standoff 2, веля стандофф 2, стандофы, со, белка, тик так, керамбит голд, как скрафтить ориджин коллекцию, читы стандофф2, hacking, root, ipa, cheating, cheats, hack, hacks, cheat, кент апк, kent.apk, видео, тиктак стрим, стримы, tictac, тиктак, standoff 2 0.37.1, standoff 0.37.1, скачать 0.37.1, стандофф 2 читы, стандофф 2 читы на телефон, как скачать читы на стандофф 2, чит стандофф 2, как скачать читы на стандофф 2 0.37.1, читы стандофф 2, чит на стандофф, стандофф 2 чит, чит на standoff 2, standoff 2 читы, скачать читы на стандофф 2, standoff 2 чит, как скачать читы на standoff 2 0.37.1, чит на standoff 2 0.37.1, читы на standoff 2, читы standoff 2, читы на стандофф 2 0.37.1, чит на стандофф 2, читы на standoff 2 0.37.1, standoff читы, раш, дата новогоднего обновления, читыстандофф, прикол, приколы, читы на стандофф 2, читы, косай, косой, wonderfull, приколыстандофф, приколыстандофф2, шерлок стандофф, 0.37.1, фрагмуви, шерлок standoff2, шерлок, обновление, обнова стандофф, эйс, kasai_standoff, касай_стандофф, дата выхода обновления 0.37.1, обновление в плей маркете, axlebolt, новогоднее обновление 0.37.1, скачать обновление, дата 0.37.1, что добавят 0.37.1, мамонт, купил аккаунты, #читstandoff #читыстандофф #чттыstandoff2 #читстандофф2 #раздачаголды #fragmovie, #standoff2​ #стандофф2​ #читыстандофф2​
#standoff2​ #стандофф2​ #читыстандофф2​ #стендофф2​, касай, касай_стандофф2, стандоф2, трейд, трейд в стандофф 2, standof2, стендоф2, стандофф 2, fragmovie, standoff, standoff 2 fragmovie, fragmovie standoff 2, стандофф, мувик стандофф 2, standoff2, фрагмуви, фрагмуви стандофф 2, стандофф 2 фрагмуви, стендофф 2, мувики стандофф 2, стэндофф 2, lusik, highlights, фрагмувик, nicky, standoff 2 0.37.1, #standoff #стандофф #standoff2 #стандофф2 #раздачаголды #fragmovie, чит на standoff 2 0.37.1, как скачать читы на standoff 2 0.37.1, shooter, fps, бесплатно, standoff читы, античит, сенса, скачать читы, бан, шутер от первого лица, читы на стандофф 2 0.37.1, читеры, стандофф 2 0.37.1, 0.37.1, аполлон_стандофф, аполлон_стандофф2, аполлон, трейд,

Скачать тут https://t.me/AimNooBsoft"""

COMMENT_TEXT = """👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft"""

TAGS = """standoff 2, стандофф, standoff, стендофф, standoff2, веля, стендофф 2, стэндофф 2, стендоф, стэндофф, standof, стандофф2, стандоф, рик, обнова 0.37.1, обновление 0.37.1, kasai_standoff2, стандофф обновление, со2, so2, стандоф 2, стендофф2, 0.37.1 стандофф 2, стендов, стандофф 2 0.37.1, 0.37.1, в стандофф 2, standoff 2 0.37.1, ric, скрафтил аркану, крафт стандофф 2, мем стандофф, мем стандофф 2, девушка в стандофф 2, wonderfull shorts, софт касай, казашка, kazashka, мафиозник, kasai софт, kasai shorts, fragmovie standoff, фрагмуви стандофф, apollon standoff 2, apollon shorts, казашка стандофф 2, мафиозник и казашка, мемы стандофф 2, мемы стандофф 2 шортс, мемы стандофф 2 без мата, смешные моменты стандофф 2, стандофф 2 мемы шортс, юкан, шортс, казашка standoff 2, казашка стандофф, девушка играет в стандофф, shorts, крафт арканы standoff 2, standoff 2 full allies gameplay, лучший игрок на телефоне в стандофф 2, fragmovie standoff 2, мувик стандофф 2, ipad pro 2020 standoff 2, айфон 7 стандофф 2, ipad pro 2021 standoff 2, frontos, лучший игрок с телефона standoff 2, мувики стандофф 2, фрагмуви стандофф 2, standoff 2 fragmovie, айпад 9 стандофф 2, стандофф 2 фрагмуви, стандофф 2 мувик, айпад 2021 стандофф 2, ipad pro 2018 standoff 2, best player standoff 2, m9 bayonet standoff 2, стендоф 2, обзор обновления 0.37.1, standoff 2 allies legend, standoff 2 allies gameplay, standoff 2 full competitive match gameplay, standoff 2 competitive gameplay, standoff 2 allies, standoff 2 ranked, standoff 2 settings, standoff 2 competitive, мувик, девушка, веля standoff 2, веля стандофф 2, читы стандофф2, hacking, root, cheating, cheats, hack, hacks, cheat, standoff 2 0.37.1, standoff 0.37.1, скачать 0.37.1, стандофф 2 читы, стандофф 2 читы на телефон, как скачать читы на стандофф 2, чит стандофф 2, как скачать читы на стандофф 2 0.37.1, читы стандофф 2, чит на стандофф, стандофф 2 чит, чит на standoff 2, standoff 2 читы, скачать читы на стандофф 2, standoff 2 чит, как скачать читы на standoff 2 0.37.1, чит на standoff 2 0.37.1, читы на standoff 2, читы standoff 2, читы на стандофф 2 0.37.1, чит на стандофф 2, читы на standoff 2 0.37.1, standoff читы, читы на стандофф 2, читы, обновление, обнова стандофф, эйс, дата выхода обновления 0.37.1, скачать обновление, дата 0.37.1, что добавят 0.37.1, трейд, трейд в стандофф 2, стандофф 2, fragmovie, standoff, standoff 2 fragmovie, fragmovie standoff 2, стандофф, мувик стандофф 2, standoff2, фрагмуви, фрагмуви стандофф 2, стандофф 2 фрагмуви, стендофф 2, мувики стандофф 2, стэндофф 2, highlights, фрагмувик, standoff 2 0.37.1, чит на standoff 2 0.37.1, как скачать читы на standoff 2 0.37.1, shooter, fps, бесплатно, standoff читы, античит, скачать читы, бан, шутер от первого лица, читы на стандофф 2 0.37.1, читеры, стандофф 2 0.37.1, 0.37.1"""

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

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class AddVideo(StatesGroup):
    waiting_for_url = State()


# ================== БАЗА ДАННЫХ ==================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                user = dict(row)
            else:
                user = {
                    "user_id": user_id, "video_count": 0, "is_completed": 0,
                    "key_issued": 0, "is_banned": 0, "registered_at": None,
                    "full_name": None, "username": None,
                }
        async with db.execute("SELECT key_value FROM issued_keys WHERE user_id = ?", (user_id,)) as cur:
            key_row = await cur.fetchone()
            user["key"] = key_row[0] if key_row else None
        async with db.execute("SELECT * FROM videos WHERE user_id = ? ORDER BY submitted_at ASC", (user_id,)) as cur:
            rows = await cur.fetchall()
            user["videos"] = [dict(r) for r in rows]
    return user


async def get_or_create_user(user_id: int, full_name: str = None, username: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
                               (user_id, full_name, username))
                await db.commit()
                return {"user_id": user_id, "full_name": full_name, "username": username,
                        "video_count": 0, "is_completed": 0, "key_issued": 0, "is_banned": 0}
            return {"user_id": user[0], "full_name": user[1], "username": user[2],
                    "video_count": user[3], "is_completed": user[4], "key_issued": user[5], "is_banned": user[6]}


async def add_video(user_id: int, video_url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO videos (user_id, video_url, status) VALUES (?, ?, 'pending')",
                        (user_id, video_url))
        await db.execute("UPDATE users SET video_count = video_count + 1 WHERE user_id = ?", (user_id,))
        async with db.execute("SELECT video_count FROM users WHERE user_id = ?", (user_id,)) as cursor:
            count = (await cursor.fetchone())[0]
            if count >= REQUIRED_VIDEOS:
                await db.execute("UPDATE users SET is_completed = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        return count


async def issue_key(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key_value FROM issued_keys WHERE user_id = ?", (user_id,)) as cursor:
            if await cursor.fetchone():
                return None
        key = f"AIM-{secrets.token_hex(8).upper()}"
        await db.execute("INSERT INTO issued_keys (user_id, key_value) VALUES (?, ?)", (user_id, key))
        await db.execute("UPDATE users SET key_issued = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        return key


async def get_stats() -> dict:
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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, full_name, username, video_count, is_completed, key_issued FROM users "
            "WHERE is_banned = 0 AND video_count > 0 ORDER BY video_count DESC, registered_at ASC LIMIT 50"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ================== КЛАВИАТУРЫ ТЕЛЕГРАМ ==================
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Открыть Mini App", web_app=WebAppInfo(url=f"{WEBAPP_URL}/app"))],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton(text="📹 Отправить видео", callback_data="add_video")],
        [InlineKeyboardButton(text="🔑 Получить ключ", callback_data="get_key")],
        [InlineKeyboardButton(text="📌 Наш канал", url=CHANNEL_LINK)]
    ])


# ================== ОБРАБОТЧИКИ ТЕЛЕГРАМ ==================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(
        f"🎯 <b>Добро пожаловать, {message.from_user.first_name}!</b>\n\n"
        f"Этот бот поможет тебе получить ключ для чита Standoff 2.\n\n"
        f"📋 <b>Как получить ключ:</b>\n"
        f"1️⃣ Найди 10 видео (тема: чит Standoff 2)\n"
        f"2️⃣ Загрузи их на YouTube (НЕ Shorts)\n"
        f"3️⃣ Отправь ссылки боту\n"
        f"4️⃣ Получи уникальный ключ активации!\n\n"
        f"📊 <b>Твой прогресс:</b> {user['video_count']}/{REQUIRED_VIDEOS}\n\n"
        f"👇 <b>Нажми на кнопку ниже, чтобы начать!</b>",
        reply_markup=get_main_keyboard(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(
        f"📊 <b>Твоя статистика</b>\n\n"
        f"🎯 Отправлено видео: <b>{user['video_count']}/{REQUIRED_VIDEOS}</b>\n"
        f"✅ Задание выполнено: {'Да' if user['is_completed'] else 'Нет'}\n"
        f"🔑 Ключ получен: {'Да' if user['key_issued'] else 'Нет'}\n"
        f"🚫 Статус: {'Заблокирован' if user['is_banned'] else 'Активен'}",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "add_video")
async def callback_add_video(callback: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    if user['is_banned']:
        await callback.answer("❌ Ваш аккаунт заблокирован!", show_alert=True)
        return
    if user['key_issued']:
        await callback.answer("✅ Вы уже получили ключ!", show_alert=True)
        return
    remaining = "ожидает проверки" if user['is_completed'] else f"{REQUIRED_VIDEOS - user['video_count']} видео"
    await callback.answer()
    await callback.message.answer(
        f"📹 <b>Отправь ссылку на YouTube видео</b>\n\nОсталось: {remaining}\n\n"
        f"<i>Формат: https://youtu.be/... или https://www.youtube.com/...</i>\n\n"
        f"📌 <b>Важно:</b> В комментариях должна быть ссылка на канал!\n{CHANNEL_LINK}",
        parse_mode="HTML"
    )
    await state.set_state(AddVideo.waiting_for_url)


@dp.message(AddVideo.waiting_for_url, F.text)
async def process_video_url(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    url = message.text.strip()
    if not (url.startswith("https://youtu.be/") or url.startswith("https://www.youtube.com/watch?v=") or url.startswith("https://youtube.com/watch?v=")):
        await message.answer("❌ <b>Неверный формат!</b>\n\nФормат: https://youtu.be/... или https://www.youtube.com/...", parse_mode="HTML")
        return
    if user['key_issued']:
        await message.answer("✅ Вы уже получили ключ!")
        await state.clear()
        return
    if user['is_completed']:
        await message.answer("✅ Все видео отправлены! Ожидайте проверки.")
        await state.clear()
        return
    video_count = await add_video(message.from_user.id, url)
    await message.answer(
        f"✅ <b>Видео принято!</b>\n\n📊 Прогресс: {video_count}/{REQUIRED_VIDEOS}\n\n"
        f"{'🎉 Задание выполнено! Ожидай проверки.' if video_count >= REQUIRED_VIDEOS else 'Продолжай!'}",
        parse_mode="HTML", reply_markup=get_main_keyboard()
    )
    await state.clear()


@dp.callback_query(F.data == "get_key")
async def callback_get_key(callback: types.CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    if user['is_banned']:
        await callback.answer("❌ Аккаунт заблокирован!", show_alert=True)
        return
    if user['key_issued']:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT key_value FROM issued_keys WHERE user_id = ?", (callback.from_user.id,)) as cursor:
                key = await cursor.fetchone()
                if key:
                    await callback.answer()
                    await callback.message.answer(f"🔑 <b>Ваш ключ:</b>\n\n<code>{key[0]}</code>\n\n📥 Скачать: {DOWNLOAD_LINK}", parse_mode="HTML")
                    return
    if not user['is_completed']:
        await callback.answer(f"❌ Осталось: {REQUIRED_VIDEOS - user['video_count']} видео", show_alert=True)
        return
    key = await issue_key(callback.from_user.id)
    if key:
        await callback.answer("🎉 Ключ выдан!", show_alert=True)
        await callback.message.answer(f"🎉 <b>Поздравляем!</b>\n\n🔑 <b>Ключ:</b>\n<code>{key}</code>\n\n📥 Скачать: {DOWNLOAD_LINK}", parse_mode="HTML")
    else:
        await callback.message.answer("❌ Ошибка. Обратитесь к администратору.")


# ================== FASTAPI ==================
def validate_init_data(init_data: str) -> dict | None:
    try:
        parsed = parse_qs(init_data)
        check_hash = parsed.get("hash", [None])[0]
        if not check_hash:
            return None
        data_check_arr = [f"{k}={v[0]}" for k, v in sorted(parsed.items()) if k != "hash"]
        data_check_string = "\n".join(data_check_arr)
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if computed_hash == check_hash:
            user_data = parsed.get("user", [None])[0]
            if user_data:
                return json.loads(unquote(user_data))
        return None
    except:
        return None


@app.get("/api/user/{user_id}")
async def api_user(user_id: int):
    try:
        return JSONResponse(await get_user_data(user_id))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/stats")
async def api_stats():
    return JSONResponse(await get_stats())


@app.get("/api/leaderboard")
async def api_leaderboard():
    return JSONResponse(await get_leaderboard())


@app.post("/api/validate")
async def api_validate(request: Request):
    body = await request.json()
    user = validate_init_data(body.get("initData", ""))
    return JSONResponse({"valid": bool(user), "user": user})


# ================== HTML ==================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
    <title>AimNoob Premium</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        :root{
            --bg:#05050a;--card:#0d0d15;--card2:#12121c;--border:#1a1a2e;
            --primary:#6366f1;--primary-glow:#818cf8;--secondary:#22d3ee;
            --accent:#f43f5e;--success:#10b981;--warning:#f59e0b;
            --text:#fff;--text2:rgba(255,255,255,.6);--text3:rgba(255,255,255,.4)
        }
        html{scroll-behavior:smooth}
        body{
            font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);
            min-height:100vh;overflow-x:hidden;-webkit-font-smoothing:antialiased
        }
        
        /* Background Effects */
        .bg-effects{position:fixed;inset:0;z-index:-1;overflow:hidden}
        .bg-grid{
            position:absolute;inset:0;
            background-image:linear-gradient(rgba(99,102,241,.03) 1px,transparent 1px),
                            linear-gradient(90deg,rgba(99,102,241,.03) 1px,transparent 1px);
            background-size:60px 60px
        }
        .bg-glow{
            position:absolute;width:600px;height:600px;border-radius:50%;
            filter:blur(120px);opacity:.15;animation:float 20s ease-in-out infinite
        }
        .bg-glow-1{background:var(--primary);top:-200px;left:-200px}
        .bg-glow-2{background:var(--secondary);bottom:-200px;right:-200px;animation-delay:-10s}
        .bg-glow-3{background:var(--accent);top:50%;left:50%;transform:translate(-50%,-50%);width:400px;height:400px;animation-delay:-5s}
        @keyframes float{0%,100%{transform:translate(0,0)}50%{transform:translate(30px,-30px)}}
        
        /* Scanlines */
        .scanlines{
            position:fixed;inset:0;z-index:1000;pointer-events:none;
            background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.03) 2px,rgba(0,0,0,.03) 4px)
        }
        
        /* Container */
        .app{max-width:440px;margin:0 auto;padding:16px;padding-bottom:90px;position:relative;z-index:1}
        
        /* Header */
        .header{text-align:center;padding:20px 0 24px}
        .logo{
            display:inline-flex;align-items:center;gap:14px;
            padding:16px 28px;background:linear-gradient(135deg,var(--card),var(--card2));
            border-radius:20px;border:1px solid var(--border);position:relative;overflow:hidden
        }
        .logo::before{
            content:'';position:absolute;inset:0;
            background:linear-gradient(135deg,transparent,rgba(99,102,241,.1),transparent);
            animation:logoShine 3s ease-in-out infinite
        }
        @keyframes logoShine{0%,100%{opacity:0}50%{opacity:1}}
        .logo-icon{
            width:52px;height:52px;background:linear-gradient(135deg,var(--primary),var(--secondary));
            border-radius:14px;display:flex;align-items:center;justify-content:center;
            font-size:26px;box-shadow:0 0 30px rgba(99,102,241,.5);position:relative
        }
        .logo-icon::after{
            content:'';position:absolute;inset:-2px;border-radius:16px;
            background:linear-gradient(135deg,var(--primary),var(--secondary));
            z-index:-1;filter:blur(10px);opacity:.5
        }
        .logo-text{
            font-size:28px;font-weight:900;letter-spacing:-1px;
            background:linear-gradient(135deg,#fff,var(--primary-glow));
            -webkit-background-clip:text;-webkit-text-fill-color:transparent
        }
        .logo-badge{
            position:absolute;top:-8px;right:-8px;background:var(--accent);
            padding:4px 10px;border-radius:8px;font-size:10px;font-weight:700;
            text-transform:uppercase;letter-spacing:.5px
        }
        .version{color:var(--text3);font-size:12px;margin-top:12px;font-weight:500}
        
        /* Status Card */
        .status-card{
            background:var(--card);border-radius:24px;padding:24px;
            border:1px solid var(--border);position:relative;overflow:hidden;margin-bottom:16px
        }
        .status-card::before{
            content:'';position:absolute;top:0;left:0;right:0;height:2px;
            background:linear-gradient(90deg,var(--primary),var(--secondary),var(--accent))
        }
        .status-card.success::before{background:linear-gradient(90deg,var(--success),#34d399)}
        .status-card.warning::before{background:linear-gradient(90deg,var(--warning),#fbbf24)}
        .status-card.danger::before{background:linear-gradient(90deg,var(--accent),#fb7185)}
        .status-inner{display:flex;gap:18px;align-items:center}
        .status-icon{
            width:70px;height:70px;border-radius:20px;display:flex;align-items:center;justify-content:center;
            font-size:36px;background:linear-gradient(135deg,rgba(99,102,241,.15),rgba(34,211,238,.1));
            border:1px solid rgba(99,102,241,.2);flex-shrink:0
        }
        .status-info{flex:1}
        .status-title{font-size:20px;font-weight:800;margin-bottom:4px;letter-spacing:-.3px}
        .status-desc{color:var(--text2);font-size:13px;line-height:1.5}
        
        /* Progress */
        .progress-section{
            background:var(--card);border-radius:24px;padding:20px;
            border:1px solid var(--border);margin-bottom:16px
        }
        .progress-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
        .progress-label{font-size:12px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px}
        .progress-value{
            font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;
            background:linear-gradient(135deg,var(--primary-glow),var(--secondary));
            -webkit-background-clip:text;-webkit-text-fill-color:transparent
        }
        .progress-bar{height:10px;background:var(--card2);border-radius:5px;overflow:hidden;position:relative}
        .progress-fill{
            height:100%;border-radius:5px;position:relative;transition:width .8s cubic-bezier(.4,0,.2,1);
            background:linear-gradient(90deg,var(--primary),var(--secondary))
        }
        .progress-fill::after{
            content:'';position:absolute;inset:0;
            background:linear-gradient(90deg,transparent,rgba(255,255,255,.4),transparent);
            animation:shine 2s linear infinite
        }
        @keyframes shine{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
        .stats-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}
        .stat-box{
            background:var(--card2);border-radius:14px;padding:14px 10px;text-align:center;
            border:1px solid var(--border);transition:all .3s
        }
        .stat-box:hover{border-color:var(--primary);transform:translateY(-2px)}
        .stat-num{
            font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;
            color:var(--primary-glow)
        }
        .stat-label{font-size:10px;color:var(--text3);margin-top:4px;text-transform:uppercase;letter-spacing:.3px}
        
        /* Nav */
        .nav{
            position:fixed;bottom:0;left:0;right:0;background:rgba(13,13,21,.95);
            backdrop-filter:blur(20px);border-top:1px solid var(--border);z-index:100;
            padding:10px 16px;padding-bottom:max(10px,env(safe-area-inset-bottom))
        }
        .nav-inner{display:flex;justify-content:space-around;max-width:440px;margin:0 auto}
        .nav-btn{
            display:flex;flex-direction:column;align-items:center;gap:4px;
            padding:8px 14px;border-radius:14px;cursor:pointer;transition:all .2s;
            background:transparent;border:none;color:var(--text3);font-family:inherit
        }
        .nav-btn:active{transform:scale(.95)}
        .nav-btn.active{color:var(--primary-glow);background:rgba(99,102,241,.12)}
        .nav-icon{font-size:22px}
        .nav-label{font-size:10px;font-weight:600}
        
        /* Sections */
        .section{display:none;animation:fadeUp .3s ease}
        .section.active{display:block}
        @keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        
        /* Cards */
        .card{
            background:var(--card);border-radius:20px;padding:20px;
            border:1px solid var(--border);margin-bottom:14px
        }
        .card-header{display:flex;align-items:center;gap:12px;margin-bottom:18px}
        .card-icon{
            width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;
            font-size:22px;background:linear-gradient(135deg,rgba(99,102,241,.15),rgba(99,102,241,.05));
            border:1px solid rgba(99,102,241,.2)
        }
        .card-title{font-size:16px;font-weight:700}
        
        /* Steps */
        .steps{display:flex;flex-direction:column;gap:12px}
        .step{
            display:flex;gap:14px;padding:16px;background:var(--card2);
            border-radius:16px;border:1px solid var(--border);transition:all .3s
        }
        .step:hover{border-color:rgba(99,102,241,.3);background:rgba(99,102,241,.03)}
        .step-num{
            width:36px;height:36px;background:linear-gradient(135deg,var(--primary),var(--primary-glow));
            border-radius:10px;display:flex;align-items:center;justify-content:center;
            font-size:14px;font-weight:800;flex-shrink:0;box-shadow:0 4px 15px rgba(99,102,241,.3)
        }
        .step-content h4{font-size:14px;font-weight:700;margin-bottom:4px}
        .step-content p{font-size:12px;color:var(--text2);line-height:1.5}
        
        /* Copy Block */
        .copy-group{margin-bottom:18px}
        .copy-label{
            font-size:11px;font-weight:600;color:var(--text3);margin-bottom:8px;
            text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center;gap:6px
        }
        .copy-box{
            background:var(--bg);border:1px solid var(--border);border-radius:14px;
            padding:14px 16px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden
        }
        .copy-box:hover{border-color:var(--primary);background:rgba(99,102,241,.03)}
        .copy-box:active{transform:scale(.99)}
        .copy-box.copied{border-color:var(--success);background:rgba(16,185,129,.05)}
        .copy-box.copied::after{
            content:'✓ Скопировано';position:absolute;top:50%;right:14px;
            transform:translateY(-50%);font-size:11px;font-weight:600;color:var(--success)
        }
        .copy-text{font-size:13px;line-height:1.6;word-break:break-word;color:var(--text)}
        .copy-text.truncate{
            display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden
        }
        
        /* Videos */
        .video-list{display:flex;flex-direction:column;gap:10px}
        .video-item{
            display:flex;align-items:center;gap:12px;padding:14px;
            background:var(--card2);border-radius:14px;border:1px solid var(--border)
        }
        .video-num{
            width:30px;height:30px;background:rgba(99,102,241,.15);border-radius:8px;
            display:flex;align-items:center;justify-content:center;
            font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;
            color:var(--primary-glow);flex-shrink:0
        }
        .video-info{flex:1;min-width:0}
        .video-link{
            color:var(--primary-glow);text-decoration:none;font-size:12px;font-weight:500;
            display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap
        }
        .video-date{font-size:10px;color:var(--text3);margin-top:2px}
        .video-badge{
            padding:6px 10px;border-radius:8px;font-size:10px;font-weight:700;
            text-transform:uppercase;letter-spacing:.3px;flex-shrink:0
        }
        .video-badge.pending{background:rgba(245,158,11,.15);color:var(--warning)}
        .video-badge.approved{background:rgba(16,185,129,.15);color:var(--success)}
        .video-badge.rejected{background:rgba(244,63,94,.15);color:var(--accent)}
        
        /* Key */
        .key-display{text-align:center;padding:20px 0}
        .key-emoji{font-size:64px;margin-bottom:16px;animation:bounce 2s ease-in-out infinite}
        @keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
        .key-title{font-size:20px;font-weight:800;margin-bottom:6px}
        .key-subtitle{color:var(--text2);font-size:13px;margin-bottom:20px}
        .key-box{
            background:linear-gradient(135deg,rgba(99,102,241,.1),rgba(34,211,238,.05));
            border:2px solid var(--primary);border-radius:16px;padding:20px;
            cursor:pointer;transition:all .2s;margin-bottom:20px
        }
        .key-box:hover{transform:scale(1.02);box-shadow:0 0 40px rgba(99,102,241,.2)}
        .key-box:active{transform:scale(.98)}
        .key-value{
            font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700;
            color:var(--primary-glow);letter-spacing:2px
        }
        .key-hint{font-size:11px;color:var(--text3);margin-top:8px}
        
        /* Leaderboard */
        .leader-list{display:flex;flex-direction:column;gap:8px}
        .leader-item{
            display:flex;align-items:center;gap:12px;padding:12px 14px;
            background:var(--card2);border-radius:14px;border:1px solid var(--border)
        }
        .leader-item.me{background:rgba(99,102,241,.08);border-color:var(--primary)}
        .leader-item.top{background:linear-gradient(135deg,rgba(245,158,11,.08),rgba(245,158,11,.02));border-color:rgba(245,158,11,.3)}
        .leader-rank{
            width:36px;height:36px;display:flex;align-items:center;justify-content:center;
            font-size:18px;flex-shrink:0
        }
        .leader-rank.num{
            font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;
            color:var(--text3);background:rgba(255,255,255,.03);border-radius:10px
        }
        .leader-user{flex:1;min-width:0}
        .leader-name{font-size:14px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .leader-username{font-size:11px;color:var(--text3)}
        .leader-score{text-align:right;flex-shrink:0}
        .leader-count{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:var(--primary-glow)}
        .leader-badge{font-size:14px;margin-top:2px}
        
        /* Buttons */
        .btn{
            display:flex;align-items:center;justify-content:center;gap:10px;
            width:100%;padding:16px;border:none;border-radius:14px;
            font-family:inherit;font-size:15px;font-weight:700;cursor:pointer;transition:all .2s
        }
        .btn:active{transform:scale(.98)}
        .btn-primary{
            background:linear-gradient(135deg,var(--primary),#4f46e5);color:#fff;
            box-shadow:0 4px 20px rgba(99,102,241,.4)
        }
        .btn-primary:hover{box-shadow:0 6px 30px rgba(99,102,241,.5);transform:translateY(-2px)}
        .btn-success{
            background:linear-gradient(135deg,var(--success),#059669);color:#fff;
            box-shadow:0 4px 20px rgba(16,185,129,.4)
        }
        .btn-outline{background:transparent;border:2px solid var(--border);color:var(--text)}
        .btn-outline:hover{border-color:var(--primary);background:rgba(99,102,241,.05)}
        
        /* Alert */
        .alert{
            padding:14px 16px;border-radius:14px;font-size:12px;
            display:flex;align-items:flex-start;gap:10px;margin-top:16px;line-height:1.5
        }
        .alert-warning{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.2);color:#fcd34d}
        .alert-icon{font-size:16px;flex-shrink:0}
        
        /* Empty */
        .empty{text-align:center;padding:40px 20px}
        .empty-icon{font-size:48px;margin-bottom:12px;opacity:.4}
        .empty-text{color:var(--text3);font-size:13px}
        
        /* Toast */
        .toast{
            position:fixed;bottom:100px;left:50%;transform:translateX(-50%) translateY(100px);
            background:var(--primary);color:#fff;padding:12px 24px;border-radius:14px;
            font-size:14px;font-weight:600;box-shadow:0 10px 40px rgba(0,0,0,.4);
            z-index:1000;opacity:0;transition:all .3s;display:flex;align-items:center;gap:8px
        }
        .toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
        
        /* Loading */
        .loading{display:flex;justify-content:center;padding:40px}
        .spinner{
            width:36px;height:36px;border:3px solid var(--border);
            border-top-color:var(--primary);border-radius:50%;animation:spin 1s linear infinite
        }
        @keyframes spin{to{transform:rotate(360deg)}}
    </style>
</head>
<body>
    <div class="bg-effects">
        <div class="bg-grid"></div>
        <div class="bg-glow bg-glow-1"></div>
        <div class="bg-glow bg-glow-2"></div>
        <div class="bg-glow bg-glow-3"></div>
    </div>
    <div class="scanlines"></div>
    
    <div class="app">
        <header class="header">
            <div class="logo">
                <div class="logo-icon">🎯</div>
                <span class="logo-text">AimNoob</span>
                <span class="logo-badge">PRO</span>
            </div>
            <div class="version">Standoff 2 Cheat • v0.37.1</div>
        </header>
        
        <div class="status-card" id="statusCard">
            <div class="status-inner">
                <div class="status-icon" id="statusIcon">🎮</div>
                <div class="status-info">
                    <div class="status-title" id="statusTitle">Загрузка...</div>
                    <div class="status-desc" id="statusDesc">Получение данных</div>
                </div>
            </div>
        </div>
        
        <div class="progress-section">
            <div class="progress-top">
                <span class="progress-label">Прогресс</span>
                <span class="progress-value" id="progressValue">0/10</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width:0%"></div>
            </div>
            <div class="stats-row">
                <div class="stat-box">
                    <div class="stat-num" id="statSent">0</div>
                    <div class="stat-label">Отправлено</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num" id="statPending">0</div>
                    <div class="stat-label">Проверка</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num" id="statApproved">0</div>
                    <div class="stat-label">Принято</div>
                </div>
            </div>
        </div>
        
        <div id="taskSection" class="section active">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📋</div>
                    <div class="card-title">Инструкция</div>
                </div>
                <div class="steps">
                    <div class="step">
                        <div class="step-num">1</div>
                        <div class="step-content">
                            <h4>Найди видео</h4>
                            <p>Берёшь видосы с TikTok из ТГ каналов с читом 0.37.1. Без водных знаков и тэгов</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">2</div>
                        <div class="step-content">
                            <h4>Выкладывай на YouTube</h4>
                            <p>Вставляешь описание, название и ссылку в комментариях (без неё не будет выдачи софта)</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">3</div>
                        <div class="step-content">
                            <h4>Как обычный ролик</h4>
                            <p>Выкладываешь его в ютуб как обычный ролик (НЕ Shorts!)</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">4</div>
                        <div class="step-content">
                            <h4>Скидывай ссылку</h4>
                            <p>После того как выложил — скидывай ссылку на видос боту</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">5</div>
                        <div class="step-content">
                            <h4>Проверка</h4>
                            <p>Я смотрю всё ли верно — описание, название, комментарий</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">6</div>
                        <div class="step-content">
                            <h4>Получи чит</h4>
                            <p>Выкладываешь ровно 10 разных видосов, говоришь "всё готово" — получаешь чит и ключ</p>
                        </div>
                    </div>
                </div>
                <div class="alert alert-warning">
                    <span class="alert-icon">⚠️</span>
                    <span>Без ссылки в комментариях на ТГК выдачи НЕ будет! Это обязательное условие.</span>
                </div>
                <button class="btn btn-primary" onclick="openBot()" style="margin-top:18px">
                    <span>📤</span> Отправить видео боту
                </button>
            </div>
        </div>
        
        <div id="dataSection" class="section">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📝</div>
                    <div class="card-title">Данные для видео</div>
                </div>
                
                <div class="copy-group">
                    <div class="copy-label"><span>🎬</span> Название</div>
                    <div class="copy-box" onclick="copyText(videoTitle,this)" id="titleBox">
                        <div class="copy-text" id="titleText"></div>
                    </div>
                </div>
                
                <div class="copy-group">
                    <div class="copy-label"><span>📄</span> Описание (вставить в описание)</div>
                    <div class="copy-box" onclick="copyText(videoDesc,this)" id="descBox">
                        <div class="copy-text truncate" id="descText"></div>
                    </div>
                </div>
                
                <div class="copy-group">
                    <div class="copy-label"><span>💬</span> Комментарий (оставить под видео)</div>
                    <div class="copy-box" onclick="copyText(commentText,this)" id="commentBox">
                        <div class="copy-text" id="commentTextEl"></div>
                    </div>
                </div>
                
                <div class="copy-group">
                    <div class="copy-label"><span>🏷️</span> Теги</div>
                    <div class="copy-box" onclick="copyText(tagsText,this)" id="tagsBox">
                        <div class="copy-text truncate" id="tagsTextEl"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="videosSection" class="section">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">📹</div>
                    <div class="card-title">Мои видео</div>
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
                <div class="card-header">
                    <div class="card-icon">🏆</div>
                    <div class="card-title">Топ участников</div>
                </div>
                <div id="leaderboardList" class="leader-list">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>
    </div>
    
    <nav class="nav">
        <div class="nav-inner">
            <button class="nav-btn active" onclick="switchTab('task')">
                <span class="nav-icon">📋</span>
                <span class="nav-label">Задание</span>
            </button>
            <button class="nav-btn" onclick="switchTab('data')">
                <span class="nav-icon">📝</span>
                <span class="nav-label">Данные</span>
            </button>
            <button class="nav-btn" onclick="switchTab('videos')">
                <span class="nav-icon">📹</span>
                <span class="nav-label">Видео</span>
            </button>
            <button class="nav-btn" onclick="switchTab('key')">
                <span class="nav-icon">🔑</span>
                <span class="nav-label">Ключ</span>
            </button>
            <button class="nav-btn" onclick="switchTab('top')">
                <span class="nav-icon">🏆</span>
                <span class="nav-label">Топ</span>
            </button>
        </div>
    </nav>
    
    <div class="toast" id="toast"><span id="toastIcon">✓</span><span id="toastText">Скопировано</span></div>

<script>
const REQUIRED=10;
const CHANNEL='https://t.me/AimNooBsoft';
const DOWNLOAD='https://t.me/AimNooBsoft';

const videoTitle=`⚡️КАК СКАЧАТЬ ЧИТ 0.37.1 STANDOFF 2 БЕЗ РУТ И БАНА ПОЛНАЯ УСТАНОВКА`;

const videoDesc=`👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft


standoff 2, стандофф, standoff, стендофф, standoff2, веля, стендофф 2, стэндофф 2, стендоф, стэндофф, standof, стандофф2, стандоф, рик, обнова 0.37.1, обновление 0.37.1, kasai_standoff2, стандофф обновление, со2, so2, стандоф 2, стендофф2, 0.37.1 стандофф 2, стендов, стандофф 2 0.37.1, 0.37.1, в стандофф 2, standoff 2 0.37.1, ric, скрафтил аркану, крафт стандофф 2, мем стандофф, мем стандофф 2, девушка в стандофф 2, wonderfull shorts, софт касай, казашка, kazashka, мафиозник, kasai софт, kasai shorts, fragmovie standoff, фрагмуви стандофф, apollon standoff 2, apollon shorts, казашка стандофф 2, мафиозник и казашка, мемы стандофф 2, мемы стандофф 2 шортс, мемы стандофф 2 без мата, смешные моменты стандофф 2, стандофф 2 мемы шортс, юкан, шортс, казашка standoff 2, казашка стандофф, девушка играет в стандофф, shorts, крафт арканы standoff 2, standoff 2 full allies gameplay, лучший игрок на телефоне в стандофф 2, fragmovie standoff 2, мувик стандофф 2, ipad pro 2020 standoff 2, айфон 7 стандофф 2, ipad pro 2021 standoff 2, frontos, лучший игрок с телефона standoff 2, мувики стандофф 2, фрагмуви стандофф 2, standoff 2 fragmovie, айпад 9 стандофф 2, стандофф 2 фрагмуви, стандофф 2 мувик, айпад 2021 стандофф 2, ipad pro 2018 standoff 2, best player standoff 2, m9 bayonet standoff 2, стендоф 2, обзор обновления 0.37.1, standoff 2 allies legend, standoff 2 allies gameplay, standoff 2 full competitive match gameplay, standoff 2 competitive gameplay, standoff 2 allies, standoff 2 ranked, standoff 2 settings, standoff 2 competitive, мувик, девушка, веля standoff 2, веля стандофф 2, читы стандофф2, hacking, root, cheating, cheats, hack, hacks, cheat, standoff 2 0.37.1, standoff 0.37.1, скачать 0.37.1, стандофф 2 читы, стандофф 2 читы на телефон, как скачать читы на стандофф 2, чит стандофф 2, как скачать читы на стандофф 2 0.37.1, читы стандофф 2, чит на стандофф, стандофф 2 чит, чит на standoff 2, standoff 2 читы, скачать читы на стандофф 2, standoff 2 чит, как скачать читы на standoff 2 0.37.1, чит на standoff 2 0.37.1, читы на standoff 2, читы standoff 2, читы на стандофф 2 0.37.1, чит на стандофф 2, читы на standoff 2 0.37.1, standoff читы, читы на стандофф 2, читы, обновление, обнова стандофф, эйс, дата выхода обновления 0.37.1, скачать обновление, дата 0.37.1, что добавят 0.37.1, трейд, трейд в стандофф 2, стандофф 2, fragmovie, standoff, standoff 2 fragmovie, fragmovie standoff 2, стандофф, мувик стандофф 2, standoff2, фрагмуви, фрагмуви стандофф 2, стандофф 2 фрагмуви, стендофф 2, мувики стандофф 2, стэндофф 2, highlights, фрагмувик, standoff 2 0.37.1, чит на standoff 2 0.37.1, как скачать читы на standoff 2 0.37.1, shooter, fps, бесплатно, standoff читы, античит, скачать читы, бан, шутер от первого лица, читы на стандофф 2 0.37.1, читеры, стандофф 2 0.37.1, 0.37.1

Скачать тут https://t.me/AimNooBsoft`;

const commentText=`👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft`;

const tagsText=`standoff 2, стандофф, standoff, стендофф, standoff2, стендофф 2, стэндофф 2, обнова 0.37.1, обновление 0.37.1, стандофф 2 0.37.1, standoff 2 0.37.1, чит стандофф 2, читы стандофф 2, чит на standoff 2, standoff 2 читы, чит на standoff 2 0.37.1, читы на standoff 2, читы на стандофф 2 0.37.1, чит на стандофф 2, standoff читы, читы на стандофф 2, читы, hacking, cheating, cheats, hack, hacks, cheat, скачать читы на стандофф 2, standoff 2 чит, как скачать читы на standoff 2 0.37.1, fragmovie, standoff 2 fragmovie, fragmovie standoff 2, мувик стандофф 2, фрагмуви, фрагмуви стандофф 2, стандофф 2 фрагмуви, мувики стандофф 2, highlights, shooter, fps, бесплатно, античит, скачать читы, бан, шутер от первого лица, читеры, 0.37.1`;

let userData=null,userId=null;
const tg=window.Telegram?.WebApp;
if(tg){tg.ready();tg.expand();tg.setHeaderColor('#05050a');tg.setBackgroundColor('#05050a');if(tg.initDataUnsafe?.user)userId=tg.initDataUnsafe.user.id}
if(!userId){const p=new URLSearchParams(location.search);userId=p.get('user_id')}

document.getElementById('titleText').textContent=videoTitle;
document.getElementById('descText').textContent=videoDesc;
document.getElementById('commentTextEl').textContent=commentText;
document.getElementById('tagsTextEl').textContent=tagsText;

async function loadUser(){
    if(!userId){updateStatus('danger','❌','Ошибка','Откройте через Telegram бота');return}
    try{const r=await fetch(`/api/user/${userId}`);userData=await r.json();renderAll()}
    catch(e){updateStatus('danger','❌','Ошибка загрузки','Попробуйте позже')}
}

async function loadLeaderboard(){
    try{const r=await fetch('/api/leaderboard');renderLeaderboard(await r.json())}
    catch(e){document.getElementById('leaderboardList').innerHTML='<div class="empty"><div class="empty-icon">❌</div><div class="empty-text">Ошибка загрузки</div></div>'}
}

function updateStatus(type,icon,title,desc){
    document.getElementById('statusCard').className='status-card '+type;
    document.getElementById('statusIcon').textContent=icon;
    document.getElementById('statusTitle').textContent=title;
    document.getElementById('statusDesc').textContent=desc;
}

function renderAll(){
    if(!userData)return;
    const count=userData.video_count||0;
    const pct=Math.min((count/REQUIRED)*100,100);
    document.getElementById('progressFill').style.width=pct+'%';
    document.getElementById('progressValue').textContent=count+'/'+REQUIRED;
    const videos=userData.videos||[];
    document.getElementById('statSent').textContent=count;
    document.getElementById('statPending').textContent=videos.filter(v=>v.status==='pending').length;
    document.getElementById('statApproved').textContent=videos.filter(v=>v.status==='approved').length;
    if(userData.is_banned)updateStatus('danger','🚫','Заблокирован','Обратитесь к администратору');
    else if(userData.key_issued&&userData.key)updateStatus('success','🎉','Ключ получен!','Скачай чит и активируй');
    else if(userData.is_completed)updateStatus('warning','⏳','На проверке','Ожидай — скоро выдам ключ');
    else if(count>0)updateStatus('','🔥','В процессе','Осталось '+(REQUIRED-count)+' видео');
    else updateStatus('','🎮','Добро пожаловать!','Выполни задание — получи чит');
    renderVideos();renderKey();
}

function renderVideos(){
    const c=document.getElementById('videosList');
    const v=userData?.videos||[];
    if(!v.length){c.innerHTML='<div class="empty"><div class="empty-icon">📭</div><div class="empty-text">Пока нет видео</div></div>';return}
    c.innerHTML=v.map((x,i)=>{
        const st=x.status==='approved'?'approved':x.status==='rejected'?'rejected':'pending';
        const stT=x.status==='approved'?'Принято':x.status==='rejected'?'Отклонено':'Проверка';
        const d=x.submitted_at?new Date(x.submitted_at).toLocaleDateString('ru-RU'):'';
        return`<div class="video-item"><div class="video-num">${i+1}</div><div class="video-info"><a href="${x.video_url}" target="_blank" class="video-link">${x.video_url}</a><div class="video-date">${d}</div></div><div class="video-badge ${st}">${stT}</div></div>`
    }).join('');
}

function renderKey(){
    const c=document.getElementById('keyContent');
    if(userData?.key){
        c.innerHTML=`<div class="key-display"><div class="key-emoji">🔑</div><div class="key-title">Твой ключ активации</div><div class="key-subtitle">Нажми чтобы скопировать</div><div class="key-box" onclick="copyKey()"><div class="key-value">${userData.key}</div><div class="key-hint">Tap to copy</div></div><button class="btn btn-success" onclick="window.open('${DOWNLOAD}','_blank')"><span>📥</span> Скачать AimNoob</button><button class="btn btn-outline" onclick="window.open('${CHANNEL}','_blank')" style="margin-top:10px"><span>📢</span> Telegram канал</button><div class="alert alert-warning"><span class="alert-icon">🔒</span><span>Ключ одноразовый — никому не передавай!</span></div></div>`;
    }else if(userData?.is_completed){
        c.innerHTML=`<div class="key-display"><div class="key-emoji">⏳</div><div class="key-title">Ожидай проверки</div><div class="key-subtitle">Все видео отправлены! Скоро выдам ключ</div><button class="btn btn-outline" onclick="window.open('${CHANNEL}','_blank')" style="margin-top:20px"><span>📢</span> Следить за новостями</button></div>`;
    }else{
        const left=REQUIRED-(userData?.video_count||0);
        c.innerHTML=`<div class="key-display"><div class="key-emoji">🔒</div><div class="key-title">Ключ недоступен</div><div class="key-subtitle">Осталось отправить <strong>${left}</strong> видео</div><button class="btn btn-primary" onclick="openBot()" style="margin-top:20px"><span>📤</span> Продолжить задание</button></div>`;
    }
}

function renderLeaderboard(data){
    const c=document.getElementById('leaderboardList');
    if(!data?.length){c.innerHTML='<div class="empty"><div class="empty-icon">🏆</div><div class="empty-text">Пока пусто</div></div>';return}
    const medals=['🥇','🥈','🥉'];
    c.innerHTML=data.map((u,i)=>{
        const me=u.user_id==userId;
        const top=i<3;
        let badge='';if(u.key_issued)badge='🔑';else if(u.is_completed)badge='✅';
        return`<div class="leader-item${me?' me':''}${top?' top':''}"><div class="leader-rank${top?'':' num'}">${top?medals[i]:i+1}</div><div class="leader-user"><div class="leader-name">${u.full_name||'User'}${me?' (Ты)':''}</div><div class="leader-username">@${u.username||'—'}</div></div><div class="leader-score"><div class="leader-count">${u.video_count}/${REQUIRED}</div><div class="leader-badge">${badge}</div></div></div>`
    }).join('');
}

function switchTab(tab){
    document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
    const tabs=['task','data','videos','key','top'];
    const i=tabs.indexOf(tab);
    if(i>=0){document.querySelectorAll('.nav-btn')[i].classList.add('active');document.getElementById(tab+'Section').classList.add('active')}
    if(tab==='top')loadLeaderboard();
    if(tg?.HapticFeedback)tg.HapticFeedback.selectionChanged();
}

function copyText(text,el){
    navigator.clipboard.writeText(text).then(()=>{
        el.classList.add('copied');setTimeout(()=>el.classList.remove('copied'),2000);
        showToast('✓','Скопировано!');
        if(tg?.HapticFeedback)tg.HapticFeedback.notificationOccurred('success');
    });
}

function copyKey(){
    if(userData?.key){navigator.clipboard.writeText(userData.key).then(()=>{showToast('🔑','Ключ скопирован!');if(tg?.HapticFeedback)tg.HapticFeedback.notificationOccurred('success')})}
}

function showToast(icon,text){
    const t=document.getElementById('toast');
    document.getElementById('toastIcon').textContent=icon;
    document.getElementById('toastText').textContent=text;
    t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000);
}

function openBot(){if(tg)tg.close();else window.open('https://t.me/AimNooBBot','_blank')}

loadUser();
</script>
</body>
</html>"""


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
    await init_db()
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot, skip_updates=True)


def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")


if __name__ == "__main__":
    logger.info("Starting AimNoob application...")
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
