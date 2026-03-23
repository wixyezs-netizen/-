import asyncio
import logging
import re
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, BotCommand
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite

# ================== КОНФИГУРАЦИЯ ==================
API_TOKEN = "8624719452:AAHBAWy6DDzXD_ekK-iI8_rAOj4lUr3PysA"
ADMIN_IDS = [8346538289]  # Список админов
REQUIRED_VIDEOS = 10
COOLDOWN_SECONDS = 1
DB_PATH = "users_data.db"
DOWNLOAD_LINK = "https://go.linkify.ru/2GPF"
CHANNEL_LINK = "https://t.me/AimNooBsoft"
# =================================================

# ================== ТЕКСТЫ ==================
TASK_DESCRIPTION = """
📋 <b>ИНСТРУКЦИЯ ПО ВЫПОЛНЕНИЮ ЗАДАНИЯ</b>

<b>1️⃣ Где брать видео?</b>
   ├ Берёте видео с TikTok из Telegram-каналов
   ├ Тематика: чит Standoff 2 0.37.1
   └ Видео должны быть <b>БЕЗ</b> водяных знаков и тегов

<b>2️⃣ Как выкладывать на YouTube?</b>
   ├ Загружаете видео как <b>ОБЫЧНЫЙ</b> ролик (НЕ Shorts)
   ├ Вставляете название (кнопка в меню)
   ├ Вставляете описание (кнопка в меню)
   └ В комментариях оставляете ссылку на TG-канал

<b>3️⃣ Что нужно сделать?</b>
   ├ Выложить <b>{required}</b> разных видео
   ├ После каждого — отправить ссылку боту
   └ После проверки — получите чит + ключ

⚠️ <b>ВАЖНО!</b> Без ссылки в комментариях выдачи не будет!
"""

VIDEO_TITLE = (
    "⚡️КАК СКАЧАТЬ ЧИТ 0.37.1 STANDOFF 2 "
    "БЕЗ РУТ И БАНА ПОЛНАЯ УСТАНОВКА"
)

VIDEO_DESCRIPTION = f"""⚡️КАК СКАЧАТЬ ЧИТ 0.37.1 STANDOFF 2 БЕЗ РУТ И БАНА ПОЛНАЯ УСТАНОВКА

👉 СКАЧАТЬ ТУТ ТГК: {CHANNEL_LINK}
👉 СКАЧАТЬ ТУТ ТГК: {CHANNEL_LINK}
👉 СКАЧАТЬ ТУТ ТГК: {CHANNEL_LINK}

#standoff2 #стандофф2 #чит #standoff2чит #стандофф2чит"""

COMMENT_TEXT = f"👉 СКАЧАТЬ ТУТ ТГК: {CHANNEL_LINK}"

TAGS = (
    "standoff 2, стандофф, standoff, стендофф, standoff2, веля, "
    "стендофф 2, стэндофф 2, стендоф, стэндофф, standof, стандофф2, "
    "стандоф, рик, обнова 0.37.1, обновление 0.37.1, kasai_standoff2, "
    "стандофф обновление, со2, so2, стандоф 2, стендофф2, "
    "0.37.1 стандофф 2, стендов, стандофф 2 0.37.1, 0.37.1, "
    "в стандофф 2, standoff 2 0.37.1, ric, скрафтил аркану, "
    "крафт стандофф 2, мем стандофф, мем стандофф 2, "
    "девушка в стандофф 2, wonderfull shorts, софт касай, "
    "казашка, kazashka, мафиозник, kasai софт, kasai shorts, "
    "fragmovie standoff, фрагмуви стандофф, apollon standoff 2, "
    "apollon shorts, казашка стандофф 2, мафиозник и казашка, "
    "мемы стандофф 2, мемы стандофф 2 шортс, "
    "мемы стандофф 2 без мата, смешные моменты стандофф 2, "
    "стандофф 2 мемы шортс, юкан, шортс, казашка standoff 2, "
    "казашка стандофф, девушка играет в стандофф, shorts, "
    "крафт арканы standoff 2, standoff 2 full allies gameplay, "
    "лучший игрок на телефоне в стандофф 2, fragmovie standoff 2, "
    "мувик стандофф 2, ipad pro 2020 standoff 2, "
    "айфон 7 стандофф 2, ipad pro 2021 standoff 2, frontos, "
    "лучший игрок с телефона standoff 2, мувики стандофф 2, "
    "фрагмуви стандофф 2, standoff 2 fragmovie, "
    "айпад 9 стандофф 2, стандофф 2 фрагмуви, "
    "стандофф 2 мувик, h9nto, айпад 2021 стандофф 2, "
    "ipad pro 2018 standoff 2, best player standoff 2, "
    "стендоф 2, обзор обновления 0.37.1, "
    "standoff 2 competitive, мувик, девушка, сталофф, belka, "
    "веля standoff 2, веля стандофф 2, стандофы, со, белка, "
    "тик так, керамбит голд, как скрафтить ориджин коллекцию, "
    "читы стандофф2, hacking, root, ipa, cheating, cheats, "
    "hack, hacks, cheat, кент апк, kent.apk, видео, "
    "тиктак стрим, стримы, tictac, тиктак, "
    "standoff 2 0.37.1, standoff 0.37.1, скачать 0.37.1, "
    "стандофф 2 читы, стандофф 2 читы на телефон, "
    "как скачать читы на стандофф 2, чит стандофф 2, "
    "как скачать читы на стандофф 2 0.37.1, читы стандофф 2, "
    "чит на стандофф, стандофф 2 чит, чит на standoff 2, "
    "standoff 2 читы, скачать читы на стандофф 2, "
    "standoff 2 чит, как скачать читы на standoff 2 0.37.1, "
    "чит на standoff 2 0.37.1, читы на standoff 2, "
    "читы standoff 2, читы на стандофф 2 0.37.1, "
    "чит на стандофф 2, читы на standoff 2 0.37.1, "
    "standoff читы, раш, дата новогоднего обновления, "
    "читыстандофф, прикол, приколы, читы на стандофф 2, "
    "читы, косай, косой, wonderfull, приколыстандофф, "
    "приколыстандофф2, шерлок стандофф, фрагмуви, "
    "шерлок standoff2, шерлок, обновление, обнова стандофф, "
    "эйс, kasai_standoff, касай_стандофф, "
    "дата выхода обновления 0.37.1, обновление в плей маркете, "
    "axlebolt, новогоднее обновление 0.37.1, "
    "скачать обновление, дата 0.37.1, что добавят 0.37.1, "
    "мамонт, купил аккаунты"
)

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)


# ================== ГЕНЕРАЦИЯ КЛЮЧЕЙ ==================
def generate_key() -> str:
    """
    Генерирует уникальный ключ в формате AIMNOOB-XXXX-XX-XXXX-XXXX
    Все сегменты — случайные HEX-символы в верхнем регистре
    """
    seg1 = secrets.token_hex(2).upper()  # 4 символа
    seg2 = secrets.token_hex(1).upper()  # 2 символа
    seg3 = secrets.token_hex(2).upper()  # 4 символа
    seg4 = secrets.token_hex(2).upper()  # 4 символа
    return f"AIMNOOB-{seg1}-{seg2}-{seg3}-{seg4}"


async def is_key_unique(key: str) -> bool:
    """Проверяет что ключ ещё не был выдан"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM issued_keys WHERE key_value = ?", (key,)
        ) as cur:
            return await cur.fetchone() is None


async def generate_unique_key() -> str:
    """Генерирует гарантированно уникальный ключ"""
    for _ in range(100):
        key = generate_key()
        if await is_key_unique(key):
            return key
    # Фоллбэк — добавляем ещё энтропии
    extra = secrets.token_hex(3).upper()
    return f"AIMNOOB-{extra[:4]}-{extra[4:6]}-{extra[6:10] if len(extra) >= 10 else secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"


async def save_issued_key(user_id: int, key: str):
    """Сохраняет выданный ключ в БД"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO issued_keys (user_id, key_value, issued_at) "
            "VALUES (?, ?, ?)",
            (user_id, key, datetime.now().isoformat())
        )
        await db.commit()


async def get_user_key(user_id: int) -> str | None:
    """Получает ключ пользователя если уже выдан"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT key_value FROM issued_keys WHERE user_id = ?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def get_all_issued_keys():
    """Получает все выданные ключи"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT ik.*, u.full_name, u.username "
            "FROM issued_keys ik "
            "LEFT JOIN users u ON ik.user_id = u.user_id "
            "ORDER BY ik.issued_at DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ================== УТИЛИТЫ ==================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def make_progress_bar(current: int, total: int, length: int = 10) -> str:
    filled = int(length * current / total) if total > 0 else 0
    filled = min(filled, length)
    return "🟩" * filled + "⬜" * (length - filled)


def format_datetime(dt_str: str | None) -> str:
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(dt_str)


# ================== БАЗА ДАННЫХ ==================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                full_name     TEXT,
                video_count   INTEGER DEFAULT 0,
                is_completed  INTEGER DEFAULT 0,
                is_banned     INTEGER DEFAULT 0,
                key_issued    INTEGER DEFAULT 0,
                registered_at TEXT,
                completed_at  TEXT,
                last_submit   TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                video_url    TEXT,
                status       TEXT DEFAULT 'pending',
                submitted_at TEXT,
                reviewed_at  TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS issued_keys (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER UNIQUE,
                key_value  TEXT UNIQUE,
                issued_at  TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id  INTEGER,
                action    TEXT,
                target_id INTEGER,
                details   TEXT,
                created_at TEXT
            )
        """)
        await db.commit()
    logger.info("Database initialized")


async def log_admin_action(
    admin_id: int, action: str,
    target_id: int = 0, details: str = ""
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admin_log "
            "(admin_id, action, target_id, details, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (admin_id, action, target_id, details,
             datetime.now().isoformat())
        )
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def register_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await get_user(user_id)
        if not existing:
            await db.execute(
                "INSERT INTO users "
                "(user_id, username, full_name, registered_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, username, full_name,
                 datetime.now().isoformat())
            )
        else:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? "
                "WHERE user_id = ?",
                (username, full_name, user_id)
            )
        await db.commit()


async def add_video(user_id: int, video_url: str) -> tuple[bool, int]:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO videos (user_id, video_url, submitted_at) "
            "VALUES (?, ?, ?)",
            (user_id, video_url, now)
        )
        await db.execute(
            "UPDATE users SET video_count = video_count + 1, "
            "last_submit = ? WHERE user_id = ?",
            (now, user_id)
        )
        await db.commit()

        async with db.execute(
            "SELECT video_count FROM users WHERE user_id = ?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            count = row[0] if row else 0

        if count >= REQUIRED_VIDEOS:
            await db.execute(
                "UPDATE users SET is_completed = 1, completed_at = ? "
                "WHERE user_id = ? AND is_completed = 0",
                (now, user_id)
            )
            await db.commit()
            return True, count

    return False, count


async def check_cooldown(user_id: int) -> int:
    user = await get_user(user_id)
    if not user or not user["last_submit"]:
        return 0
    try:
        last = datetime.fromisoformat(user["last_submit"])
        diff = (datetime.now() - last).total_seconds()
        remaining = COOLDOWN_SECONDS - diff
        return max(0, int(remaining))
    except Exception:
        return 0


async def check_duplicate_url(user_id: int, url: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM videos "
            "WHERE user_id = ? AND video_url = ?",
            (user_id, url)
        ) as cur:
            return await cur.fetchone() is not None


async def check_global_duplicate_url(url: str) -> dict | None:
    """Проверяет не отправлял ли эту ссылку другой пользователь"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT v.*, u.full_name, u.username FROM videos v "
            "JOIN users u ON v.user_id = u.user_id "
            "WHERE v.video_url = ? LIMIT 1",
            (url,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_pending_videos(offset: int = 0, limit: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT v.id, v.user_id, v.video_url, v.submitted_at, "
            "u.username, u.full_name, u.video_count "
            "FROM videos v JOIN users u ON v.user_id = u.user_id "
            "WHERE v.status = 'pending' "
            "ORDER BY v.submitted_at ASC LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def count_pending_videos() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM videos WHERE status = 'pending'"
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def update_video_status(video_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE videos SET status = ?, reviewed_at = ? "
            "WHERE id = ?",
            (status, datetime.now().isoformat(), video_id)
        )
        await db.commit()


async def get_video_user_id(video_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM videos WHERE id = ?", (video_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def decrement_video_count(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET video_count = MAX(0, video_count - 1), "
            "is_completed = 0 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def mark_key_issued(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET key_issued = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_statistics() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        queries = {
            "total_users": "SELECT COUNT(*) FROM users",
            "completed_users":
                "SELECT COUNT(*) FROM users WHERE is_completed = 1",
            "keys_issued":
                "SELECT COUNT(*) FROM users WHERE key_issued = 1",
            "banned_users":
                "SELECT COUNT(*) FROM users WHERE is_banned = 1",
            "total_videos": "SELECT COUNT(*) FROM videos",
            "pending_videos":
                "SELECT COUNT(*) FROM videos WHERE status = 'pending'",
            "approved_videos":
                "SELECT COUNT(*) FROM videos WHERE status = 'approved'",
            "rejected_videos":
                "SELECT COUNT(*) FROM videos WHERE status = 'rejected'",
            "total_keys":
                "SELECT COUNT(*) FROM issued_keys",
        }
        for key, query in queries.items():
            async with db.execute(query) as c:
                stats[key] = (await c.fetchone())[0]

        cutoff = (
            datetime.now() - timedelta(hours=24)
        ).isoformat()
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE registered_at >= ?",
            (cutoff,)
        ) as c:
            stats["new_today"] = (await c.fetchone())[0]

        return stats


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE is_banned = 0"
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def get_completed_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users "
            "WHERE is_completed = 1 AND key_issued = 0 "
            "AND is_banned = 0 "
            "ORDER BY completed_at ASC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_user_videos(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM videos WHERE user_id = ? "
            "ORDER BY submitted_at ASC",
            (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ================== СОСТОЯНИЯ FSM ==================
class VideoState(StatesGroup):
    waiting_for_link = State()


class AdminState(StatesGroup):
    waiting_broadcast = State()
    waiting_user_info_id = State()
    waiting_ban_id = State()
    waiting_unban_id = State()
    waiting_custom_key = State()
    waiting_reject_reason = State()


# ================== КЛАВИАТУРЫ ==================
def kb_main(user_id: int | None = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text="📖 Задание", callback_data="task"
        ),
         InlineKeyboardButton(
             text="📊 Прогресс", callback_data="progress"
         )],
        [InlineKeyboardButton(
            text="📝 Данные для видео", callback_data="data_menu"
        )],
        [InlineKeyboardButton(
            text="📤 Отправить ссылку", callback_data="send_link"
        )],
        [InlineKeyboardButton(
            text="📜 Мои видео", callback_data="my_videos"
        ),
         InlineKeyboardButton(
             text="🔑 Мой ключ", callback_data="my_key"
         )],
        [InlineKeyboardButton(
            text="❓ Помощь", callback_data="help"
        )]
    ]
    if user_id and is_admin(user_id):
        buttons.append([InlineKeyboardButton(
            text="🔐 Админ-панель", callback_data="admin_panel"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_data_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Название", callback_data="d_title"
        ),
         InlineKeyboardButton(
             text="📄 Описание", callback_data="d_desc"
         )],
        [InlineKeyboardButton(
            text="💬 Комментарий", callback_data="d_comment"
        ),
         InlineKeyboardButton(
             text="🏷 Теги", callback_data="d_tags"
         )],
        [InlineKeyboardButton(
            text="📋 Всё сразу", callback_data="d_all"
        )],
        [InlineKeyboardButton(
            text="🔙 Меню", callback_data="menu"
        )]
    ])


def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔍 Проверка видео", callback_data="a_check"
        ),
         InlineKeyboardButton(
             text="📊 Статистика", callback_data="a_stats"
         )],
        [InlineKeyboardButton(
            text="🎁 Выдать ключ", callback_data="a_keys"
        ),
         InlineKeyboardButton(
             text="🔑 Все ключи", callback_data="a_all_keys"
         )],
        [InlineKeyboardButton(
            text="📢 Рассылка", callback_data="a_broadcast"
        ),
         InlineKeyboardButton(
             text="👤 Инфо юзера", callback_data="a_user_info"
         )],
        [InlineKeyboardButton(
            text="🚫 Бан", callback_data="a_ban"
        ),
         InlineKeyboardButton(
             text="✅ Разбан", callback_data="a_unban"
         )],
        [InlineKeyboardButton(
            text="🔙 Меню", callback_data="menu"
        )]
    ])


def kb_video_review(
    video_id: int, offset: int, total: int
) -> InlineKeyboardMarkup:
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Пред.", callback_data=f"a_nav_{offset - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"📄 {offset + 1}/{total}", callback_data="noop"
    ))
    if offset < total - 1:
        nav.append(InlineKeyboardButton(
            text="След. ➡️", callback_data=f"a_nav_{offset + 1}"
        ))

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Принять",
                callback_data=f"approve_{video_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_{video_id}"
            )
        ],
        [InlineKeyboardButton(
            text="🔗 Открыть видео",
            callback_data=f"open_video_{video_id}"
        )],
        nav,
        [InlineKeyboardButton(
            text="🔙 Админ-панель", callback_data="admin_panel"
        )]
    ])


def kb_back_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔙 Админ-панель", callback_data="admin_panel"
        )]
    ])


def kb_back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔙 Меню", callback_data="menu"
        )]
    ])


def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отмена", callback_data="cancel"
        )]
    ])


def kb_confirm_key(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔑 Авто-ключ",
                callback_data=f"auto_key_{user_id}"
            ),
            InlineKeyboardButton(
                text="✏️ Свой ключ",
                callback_data=f"custom_key_{user_id}"
            )
        ],
        [InlineKeyboardButton(
            text="🔙 Назад", callback_data="a_keys"
        )]
    ])


# ================== ОБРАБОТЧИКИ ==================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    uname = message.from_user.username or "—"
    fname = message.from_user.full_name

    await register_user(uid, uname, fname)
    user = await get_user(uid)

    if user and user["is_banned"]:
        await message.answer(
            "🚫 <b>Ваш аккаунт заблокирован.</b>\n"
            "Обратитесь к администратору.",
            parse_mode="HTML"
        )
        return

    count = user["video_count"] if user else 0
    bar = make_progress_bar(count, REQUIRED_VIDEOS)

    # Статус
    if user and user["key_issued"]:
        status_line = "🎉 Ключ получен!"
    elif user and user["is_completed"]:
        status_line = "✅ Ожидай проверки админом"
    elif count > 0:
        status_line = f"⏳ Осталось: {REQUIRED_VIDEOS - count} видео"
    else:
        status_line = "🆕 Начни выполнять задание!"

    text = (
        f"👋 <b>Привет, {fname}!</b>\n\n"
        f"🎮 Выполни задание и получи чит Standoff 2\n\n"
        f"📊 {bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n"
        f"📌 {status_line}\n\n"
        f"Выбери действие 👇"
    )
    await message.answer(
        text, reply_markup=kb_main(uid), parse_mode="HTML"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    pending = await count_pending_videos()
    await message.answer(
        f"🔐 <b>Админ-панель</b>\n\n"
        f"📬 На проверке: <b>{pending}</b> видео",
        reply_markup=kb_admin(), parse_mode="HTML"
    )


# --- Навигация ---
@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = callback.from_user.id
    user = await get_user(uid)
    count = user["video_count"] if user else 0
    bar = make_progress_bar(count, REQUIRED_VIDEOS)

    text = (
        f"🏠 <b>Главное меню</b>\n\n"
        f"📊 {bar} <b>{count}/{REQUIRED_VIDEOS}</b>"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_main(uid), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_main(uid), parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "❌ Действие отменено.",
            reply_markup=kb_back_menu()
        )
    except Exception:
        await callback.message.answer(
            "❌ Действие отменено.",
            reply_markup=kb_back_menu()
        )
    await callback.answer()


# --- Задание ---
@dp.callback_query(F.data == "task")
async def cb_task(callback: CallbackQuery):
    text = TASK_DESCRIPTION.format(required=REQUIRED_VIDEOS)
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    await callback.answer()


# --- Помощь ---
@dp.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    text = (
        "❓ <b>Частые вопросы</b>\n\n"
        "▫️ <b>Где брать видео?</b>\n"
        "  Из TG-каналов по тематике Standoff 2\n\n"
        "▫️ <b>Какой формат ссылки?</b>\n"
        "  <code>https://youtu.be/XXXXX</code>\n"
        "  <code>https://youtube.com/watch?v=XXXXX</code>\n\n"
        f"▫️ <b>Сколько видео нужно?</b>\n"
        f"  {REQUIRED_VIDEOS} штук\n\n"
        "▫️ <b>Когда получу ключ?</b>\n"
        "  После проверки всех видео админом\n\n"
        "▫️ <b>Видео отклонили?</b>\n"
        "  Перечитай инструкцию, загрузи заново\n\n"
        "▫️ <b>Что за ключ?</b>\n"
        "  Уникальный ключ формата AIMNOOB-XXXX-XX-XXXX-XXXX\n\n"
        "📩 По вопросам — пиши админу"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    await callback.answer()


# --- Мой ключ ---
@dp.callback_query(F.data == "my_key")
async def cb_my_key(callback: CallbackQuery):
    uid = callback.from_user.id
    user = await get_user(uid)

    if not user:
        await callback.answer("Нажми /start", show_alert=True)
        return

    key = await get_user_key(uid)
    if key:
        text = (
            "🔑 <b>Твой ключ:</b>\n\n"
            f"<code>{key}</code>\n\n"
            f"📥 <b>Скачать чит:</b>\n"
            f"{DOWNLOAD_LINK}\n\n"
            f"📌 Инструкция в канале: {CHANNEL_LINK}"
        )
    elif user["is_completed"]:
        text = (
            "⏳ <b>Задание выполнено!</b>\n\n"
            "Ключ ещё не выдан — ожидай проверки админом.\n"
            "Обычно это занимает до 24ч."
        )
    else:
        remaining = REQUIRED_VIDEOS - user["video_count"]
        text = (
            "🔑 <b>Ключ пока не доступен</b>\n\n"
            f"Осталось отправить: {remaining} видео\n"
            "Выполни задание полностью!"
        )

    try:
        await callback.message.edit_text(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    await callback.answer()


# --- Данные для видео ---
@dp.callback_query(F.data == "data_menu")
async def cb_data_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "📝 <b>Данные для видео</b>\n\n"
            "Выбери что скопировать:",
            reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "📝 <b>Данные для видео</b>\n\n"
            "Выбери что скопировать:",
            reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data == "d_title")
async def cb_title(callback: CallbackQuery):
    text = (
        f"📝 <b>Название видео:</b>\n\n"
        f"<code>{VIDEO_TITLE}</code>\n\n"
        f"👆 Нажми на текст чтобы скопировать"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data == "d_desc")
async def cb_desc(callback: CallbackQuery):
    text = (
        f"📄 <b>Описание видео:</b>\n\n"
        f"<code>{VIDEO_DESCRIPTION}</code>\n\n"
        f"👆 Нажми на текст чтобы скопировать"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data == "d_comment")
async def cb_comment(callback: CallbackQuery):
    text = (
        f"💬 <b>Комментарий:</b>\n\n"
        f"<code>{COMMENT_TEXT}</code>\n\n"
        f"⚠️ <b>ОБЯЗАТЕЛЬНО</b> оставь этот комментарий!\n"
        f"Без него выдачи не будет."
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data == "d_tags")
async def cb_tags(callback: CallbackQuery):
    text = (
        "🏷 <b>Теги:</b>\n\n"
        f"<code>{TAGS[:3500]}</code>\n\n"
        "👆 Нажми чтобы скопировать\n"
        "Вставь в описание видео"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data == "d_all")
async def cb_all_data(callback: CallbackQuery):
    text = (
        "📋 <b>ВСЕ ДАННЫЕ ДЛЯ ВИДЕО</b>\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Название:</b>\n"
        f"<code>{VIDEO_TITLE}</code>\n\n"
        f"📄 <b>Описание:</b>\n"
        f"<code>{VIDEO_DESCRIPTION}</code>\n\n"
        f"💬 <b>Комментарий:</b>\n"
        f"<code>{COMMENT_TEXT}</code>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "☝️ Нажимай на тексты для копирования"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_data_menu(), parse_mode="HTML"
        )
    await callback.answer()


# --- Прогресс ---
@dp.callback_query(F.data == "progress")
async def cb_progress(callback: CallbackQuery):
    uid = callback.from_user.id
    user = await get_user(uid)
    if not user:
        await callback.answer("Нажми /start", show_alert=True)
        return

    count = user["video_count"]
    bar = make_progress_bar(count, REQUIRED_VIDEOS)
    remaining = max(0, REQUIRED_VIDEOS - count)

    if user["key_issued"]:
        status = "🎉 Ключ получен!"
    elif user["is_completed"]:
        status = "✅ Задание выполнено — ожидай проверки"
    elif count > 0:
        status = f"⏳ Осталось: {remaining} видео"
    else:
        status = "🆕 Задание не начато"

    reg = format_datetime(user.get("registered_at"))
    key = await get_user_key(uid)
    key_line = (
        f"\n🔑 Ключ: <code>{key}</code>" if key
        else ""
    )

    text = (
        f"📊 <b>Твой прогресс</b>\n\n"
        f"{bar}\n"
        f"<b>{count} / {REQUIRED_VIDEOS} видео</b>\n\n"
        f"📌 Статус: {status}\n"
        f"📅 Регистрация: {reg}"
        f"{key_line}"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    await callback.answer()


# --- Мои видео ---
@dp.callback_query(F.data == "my_videos")
async def cb_my_videos(callback: CallbackQuery):
    uid = callback.from_user.id
    videos = await get_user_videos(uid)

    if not videos:
        try:
            await callback.message.edit_text(
                "📜 У тебя пока нет отправленных видео.\n"
                "Начни выполнять задание!",
                reply_markup=kb_back_menu()
            )
        except Exception:
            await callback.message.answer(
                "📜 У тебя пока нет отправленных видео.",
                reply_markup=kb_back_menu()
            )
        await callback.answer()
        return

    status_emoji = {
        "pending": "🕐", "approved": "✅", "rejected": "❌"
    }
    status_text = {
        "pending": "На проверке",
        "approved": "Принято",
        "rejected": "Отклонено"
    }

    lines = [f"📜 <b>Твои видео ({len(videos)}):</b>\n"]
    for i, v in enumerate(videos, 1):
        emoji = status_emoji.get(v["status"], "❓")
        st = status_text.get(v["status"], v["status"])
        dt = format_datetime(v["submitted_at"])
        lines.append(
            f"<b>{i}.</b> {emoji} {st}\n"
            f"   🔗 {v['video_url']}\n"
            f"   📅 {dt}"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n... и другие"

    try:
        await callback.message.edit_text(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_back_menu(), parse_mode="HTML"
        )
    await callback.answer()


# --- Отправка ссылки ---
@dp.callback_query(F.data == "send_link")
async def cb_send_link(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    user = await get_user(uid)

    if not user:
        await callback.answer("Нажми /start", show_alert=True)
        return

    if user["is_banned"]:
        await callback.answer(
            "🚫 Вы заблокированы", show_alert=True
        )
        return

    if user["key_issued"]:
        await callback.answer(
            "🎉 Ты уже получил ключ!", show_alert=True
        )
        return

    if user["video_count"] >= REQUIRED_VIDEOS:
        try:
            await callback.message.edit_text(
                f"✅ Все {REQUIRED_VIDEOS} видео отправлены!\n"
                "Ожидай проверки администратором.",
                reply_markup=kb_back_menu()
            )
        except Exception:
            pass
        await callback.answer()
        return

    cd = await check_cooldown(uid)
    if cd > 0:
        await callback.answer(
            f"⏳ Подожди {cd} сек.", show_alert=True
        )
        return

    count = user["video_count"]
    bar = make_progress_bar(count, REQUIRED_VIDEOS)

    try:
        await callback.message.edit_text(
            f"📤 <b>Отправка видео #{count + 1}</b>\n\n"
            f"{bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n\n"
            f"Отправь ссылку на YouTube видео 👇\n\n"
            f"Форматы:\n"
            f"• <code>https://youtu.be/XXXXX</code>\n"
            f"• <code>https://youtube.com/watch?v=XXXXX</code>\n"
            f"• <code>https://youtube.com/shorts/XXXXX</code>",
            reply_markup=kb_cancel(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"📤 Отправь ссылку на YouTube видео #{count + 1}:",
            reply_markup=kb_cancel()
        )
    await state.set_state(VideoState.waiting_for_link)
    await callback.answer()


@dp.message(VideoState.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    uid = message.from_user.id
    url = message.text.strip() if message.text else ""

    user = await get_user(uid)
    if not user:
        await state.clear()
        await message.answer("Ошибка. Нажми /start")
        return

    if user["is_banned"]:
        await state.clear()
        await message.answer("🚫 Вы заблокированы.")
        return

    # Валидация YouTube
    yt_pattern = (
        r'(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)'
        r'|youtu\.be/)[\w\-]+'
    )
    if not re.match(yt_pattern, url):
        await message.answer(
            "❌ <b>Неверная ссылка!</b>\n\n"
            "Допустимые форматы:\n"
            "• <code>https://youtu.be/XXXXX</code>\n"
            "• <code>https://youtube.com/watch?v=XXXXX</code>\n"
            "• <code>https://youtube.com/shorts/XXXXX</code>\n\n"
            "Попробуй ещё раз 👇",
            parse_mode="HTML"
        )
        return

    # Дубликат у себя
    if await check_duplicate_url(uid, url):
        await message.answer(
            "⚠️ Ты уже отправлял эту ссылку! "
            "Отправь другое видео."
        )
        return

    # Глобальный дубликат
    global_dup = await check_global_duplicate_url(url)
    if global_dup and global_dup["user_id"] != uid:
        await message.answer(
            "⚠️ Это видео уже отправил другой пользователь!\n"
            "Загрузи своё уникальное видео."
        )
        return

    # Кулдаун
    cd = await check_cooldown(uid)
    if cd > 0:
        await message.answer(f"⏳ Подожди {cd} сек.")
        return

    completed, count = await add_video(uid, url)
    bar = make_progress_bar(count, REQUIRED_VIDEOS)

    if completed:
        text = (
            f"✅ <b>Видео #{count} добавлено!</b>\n\n"
            f"{bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n\n"
            f"🎉 <b>Все видео отправлены!</b>\n"
            f"Администратор проверит и выдаст ключ.\n"
            f"Ожидай — обычно до 24ч."
        )
        await message.answer(
            text, reply_markup=kb_main(uid), parse_mode="HTML"
        )
        # Уведомление админам
        for aid in ADMIN_IDS:
            try:
                await bot.send_message(
                    aid,
                    f"🎉 <b>ЗАДАНИЕ ВЫПОЛНЕНО!</b>\n\n"
                    f"👤 {message.from_user.full_name} "
                    f"(@{message.from_user.username or '—'})\n"
                    f"🆔 <code>{uid}</code>\n"
                    f"📹 Отправлено {count} видео\n\n"
                    f"Пора проверять!",
                    parse_mode="HTML", reply_markup=kb_admin()
                )
            except Exception:
                pass
    else:
        remaining = REQUIRED_VIDEOS - count
        text = (
            f"✅ <b>Видео #{count} добавлено!</b>\n\n"
            f"{bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n"
            f"⏳ Осталось: {remaining}\n\n"
            f"Отправь следующую ссылку или вернись в меню."
        )
        await message.answer(
            text, reply_markup=kb_main(uid), parse_mode="HTML"
        )

    await state.clear()


# ================== АДМИН ==================

@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    await state.clear()
    pending = await count_pending_videos()
    try:
        await callback.message.edit_text(
            f"🔐 <b>Админ-панель</b>\n\n"
            f"📬 На проверке: <b>{pending}</b> видео",
            reply_markup=kb_admin(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"🔐 <b>Админ-панель</b>\n\n"
            f"📬 На проверке: <b>{pending}</b> видео",
            reply_markup=kb_admin(), parse_mode="HTML"
        )
    await callback.answer()


# --- Статистика ---
@dp.callback_query(F.data == "a_stats")
async def cb_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    s = await get_statistics()
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{s['total_users']}</b>\n"
        f"🆕 За 24ч: <b>{s['new_today']}</b>\n"
        f"✅ Выполнили задание: <b>{s['completed_users']}</b>\n"
        f"🔑 Ключей выдано: <b>{s['keys_issued']}</b> "
        f"(в БД: {s['total_keys']})\n"
        f"🚫 Забанено: <b>{s['banned_users']}</b>\n\n"
        f"📹 <b>Видео:</b>\n"
        f"├ Всего: <b>{s['total_videos']}</b>\n"
        f"├ 🕐 На проверке: <b>{s['pending_videos']}</b>\n"
        f"├ ✅ Принято: <b>{s['approved_videos']}</b>\n"
        f"└ ❌ Отклонено: <b>{s['rejected_videos']}</b>"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=kb_back_admin(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_back_admin(), parse_mode="HTML"
        )
    await callback.answer()


# --- Все выданные ключи ---
@dp.callback_query(F.data == "a_all_keys")
async def cb_all_keys(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    keys = await get_all_issued_keys()
    if not keys:
        try:
            await callback.message.edit_text(
                "🔑 Ещё ни одного ключа не выдано.",
                reply_markup=kb_back_admin()
            )
        except Exception:
            pass
        await callback.answer()
        return

    lines = [f"🔑 <b>Выданные ключи ({len(keys)}):</b>\n"]
    for k in keys:
        dt = format_datetime(k.get("issued_at"))
        name = k.get("full_name", "?")
        uname = k.get("username", "—")
        lines.append(
            f"👤 {name} (@{uname})\n"
            f"   🆔 <code>{k['user_id']}</code>\n"
            f"   🔑 <code>{k['key_value']}</code>\n"
            f"   📅 {dt}\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n... и другие"

    try:
        await callback.message.edit_text(
            text, reply_markup=kb_back_admin(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb_back_admin(), parse_mode="HTML"
        )
    await callback.answer()


# --- Проверка видео ---
@dp.callback_query(F.data == "a_check")
async def cb_check_videos(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    await show_review_page(callback, 0)


@dp.callback_query(F.data.startswith("a_nav_"))
async def cb_nav_review(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    offset = int(callback.data.split("_")[2])
    await show_review_page(callback, offset)


async def show_review_page(callback: CallbackQuery, offset: int):
    total = await count_pending_videos()
    if total == 0:
        try:
            await callback.message.edit_text(
                "📭 Нет видео на проверку!",
                reply_markup=kb_back_admin()
            )
        except Exception:
            await callback.message.answer(
                "📭 Нет видео на проверку!",
                reply_markup=kb_back_admin()
            )
        await callback.answer()
        return

    offset = min(offset, total - 1)
    videos = await get_pending_videos(offset=offset, limit=1)

    if not videos:
        try:
            await callback.message.edit_text(
                "📭 Нет видео на проверку!",
                reply_markup=kb_back_admin()
            )
        except Exception:
            pass
        await callback.answer()
        return

    v = videos[0]
    dt = format_datetime(v["submitted_at"])

    text = (
        f"🔍 <b>Проверка видео</b>  ({offset + 1}/{total})\n\n"
        f"👤 <b>{v['full_name']}</b> "
        f"(@{v['username'] or '—'})\n"
        f"🆔 <code>{v['user_id']}</code>\n"
        f"📊 Видео: {v['video_count']}/{REQUIRED_VIDEOS}\n"
        f"📅 Отправлено: {dt}\n\n"
        f"🔗 {v['video_url']}"
    )

    kb = kb_video_review(v["id"], offset, total)
    try:
        await callback.message.edit_text(
            text, reply_markup=kb, parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb, parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("open_video_"))
async def cb_open_video(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    video_id = int(callback.data.split("_")[2])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT video_url FROM videos WHERE id = ?",
            (video_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                await callback.answer(
                    f"Ссылка: {row[0]}", show_alert=True
                )
            else:
                await callback.answer("Видео не найдено")


@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    video_id = int(callback.data.split("_")[1])
    await update_video_status(video_id, "approved")
    user_id = await get_video_user_id(video_id)

    await log_admin_action(
        callback.from_user.id, "approve_video",
        target_id=user_id or 0,
        details=f"video_id={video_id}"
    )

    if user_id:
        try:
            user = await get_user(user_id)
            count = user["video_count"] if user else 0
            bar = make_progress_bar(count, REQUIRED_VIDEOS)
            await bot.send_message(
                user_id,
                f"✅ <b>Видео одобрено!</b>\n\n"
                f"{bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n"
                f"Продолжай в том же духе! 💪",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer("✅ Видео одобрено!")
    await show_review_page(callback, 0)


@dp.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    video_id = int(callback.data.split("_")[1])
    await state.update_data(reject_video_id=video_id)

    try:
        await callback.message.edit_text(
            "❌ <b>Отклонение видео</b>\n\n"
            "Отправь причину отклонения "
            "(или <code>стандарт</code> для стандартной):",
            reply_markup=kb_cancel(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "Отправь причину отклонения:",
            reply_markup=kb_cancel()
        )
    await state.set_state(AdminState.waiting_reject_reason)
    await callback.answer()


@dp.message(AdminState.waiting_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    video_id = data.get("reject_video_id")
    if not video_id:
        await state.clear()
        await message.answer("Ошибка.", reply_markup=kb_admin())
        return

    reason_text = message.text.strip()
    if reason_text.lower() in ("стандарт", "стандартная", "default"):
        reason_text = (
            "Не соответствует требованиям.\n"
            "Проверь:\n"
            "• Видео без водяных знаков?\n"
            "• Название верное?\n"
            "• Описание верное?\n"
            "• Комментарий со ссылкой оставлен?"
        )

    await update_video_status(video_id, "rejected")
    user_id = await get_video_user_id(video_id)

    await log_admin_action(
        message.from_user.id, "reject_video",
        target_id=user_id or 0,
        details=f"video_id={video_id}, reason={reason_text}"
    )

    if user_id:
        await decrement_video_count(user_id)
        try:
            user = await get_user(user_id)
            count = user["video_count"] if user else 0
            bar = make_progress_bar(count, REQUIRED_VIDEOS)
            await bot.send_message(
                user_id,
                f"❌ <b>Видео отклонено!</b>\n\n"
                f"📝 <b>Причина:</b> {reason_text}\n\n"
                f"{bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n\n"
                f"Загрузи верное видео и отправь ссылку.",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await message.answer(
        "❌ Видео отклонено, пользователь уведомлён.",
        reply_markup=kb_admin()
    )
    await state.clear()


# --- Выдача ключей ---
@dp.callback_query(F.data == "a_keys")
async def cb_keys_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    users = await get_completed_users()
    if not users:
        try:
            await callback.message.edit_text(
                "📭 Нет пользователей для выдачи ключа.",
                reply_markup=kb_back_admin()
            )
        except Exception:
            pass
        await callback.answer()
        return

    buttons = []
    for u in users:
        buttons.append([InlineKeyboardButton(
            text=(
                f"🎁 {u['full_name']} "
                f"(@{u['username'] or '—'}) "
                f"[{u['video_count']}/{REQUIRED_VIDEOS}]"
            ),
            callback_data=f"select_key_{u['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Админ-панель", callback_data="admin_panel"
    )])

    try:
        await callback.message.edit_text(
            f"🎁 <b>Выдача ключей</b>\n\n"
            f"Готовы: <b>{len(users)}</b> чел.\n"
            f"Выбери пользователя:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons
            ),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"🎁 Выдача ключей — {len(users)} чел.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons
            )
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("select_key_"))
async def cb_select_key(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[2])
    user = await get_user(user_id)
    name = user["full_name"] if user else str(user_id)

    # Генерируем превью ключа
    preview_key = await generate_unique_key()

    try:
        await callback.message.edit_text(
            f"🔑 <b>Выдача ключа</b>\n\n"
            f"👤 {name} "
            f"(@{user['username'] or '—' if user else '—'})\n"
            f"🆔 <code>{user_id}</code>\n\n"
            f"🎲 Авто-ключ: <code>{preview_key}</code>\n\n"
            f"Выбери способ:",
            reply_markup=kb_confirm_key(user_id),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"Выдача ключа для {name}:",
            reply_markup=kb_confirm_key(user_id)
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("auto_key_"))
async def cb_auto_key(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[2])

    # Проверяем не выдан ли уже
    existing = await get_user_key(user_id)
    if existing:
        await callback.answer(
            f"Ключ уже выдан: {existing}", show_alert=True
        )
        return

    # Генерируем уникальный ключ
    key = await generate_unique_key()
    await save_issued_key(user_id, key)
    await mark_key_issued(user_id)

    await log_admin_action(
        callback.from_user.id, "issue_key",
        target_id=user_id, details=f"key={key}"
    )

    # Отправляем пользователю
    key_message = (
        "🎉 <b>ПОЗДРАВЛЯЮ! ЗАДАНИЕ ВЫПОЛНЕНО!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>Твой уникальный ключ:</b>\n\n"
        f"<code>{key}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"📥 <b>Скачать чит:</b>\n"
        f"{DOWNLOAD_LINK}\n\n"
        f"📌 Инструкция в канале: {CHANNEL_LINK}\n\n"
        "⚠️ Ключ одноразовый — никому не передавай!"
    )

    try:
        await bot.send_message(
            user_id, key_message, parse_mode="HTML"
        )
        try:
            await callback.message.edit_text(
                f"✅ <b>Ключ выдан!</b>\n\n"
                f"👤 ID: <code>{user_id}</code>\n"
                f"🔑 <code>{key}</code>",
                reply_markup=kb_admin(), parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                f"✅ Ключ выдан: {key}",
                reply_markup=kb_admin()
            )
    except Exception as e:
        await callback.message.answer(
            f"❌ Ошибка отправки: {e}\n"
            f"Ключ: <code>{key}</code>",
            reply_markup=kb_admin(), parse_mode="HTML"
        )

    await callback.answer("✅ Ключ выдан!")


@dp.callback_query(F.data.startswith("custom_key_"))
async def cb_custom_key(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[2])
    await state.update_data(issue_user_id=user_id)

    try:
        await callback.message.edit_text(
            "✏️ <b>Свой ключ</b>\n\n"
            "Отправь ключ для выдачи пользователю:",
            reply_markup=kb_cancel(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "Отправь ключ:", reply_markup=kb_cancel()
        )
    await state.set_state(AdminState.waiting_custom_key)
    await callback.answer()


@dp.message(AdminState.waiting_custom_key)
async def process_custom_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    user_id = data.get("issue_user_id")
    if not user_id:
        await state.clear()
        await message.answer("Ошибка.", reply_markup=kb_admin())
        return

    key = message.text.strip()

    # Проверяем не выдан ли
    existing = await get_user_key(user_id)
    if existing:
        await message.answer(
            f"⚠️ Ключ уже выдан: <code>{existing}</code>",
            reply_markup=kb_admin(), parse_mode="HTML"
        )
        await state.clear()
        return

    await save_issued_key(user_id, key)
    await mark_key_issued(user_id)

    await log_admin_action(
        message.from_user.id, "issue_custom_key",
        target_id=user_id, details=f"key={key}"
    )

    key_message = (
        "🎉 <b>ПОЗДРАВЛЯЮ! ЗАДАНИЕ ВЫПОЛНЕНО!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>Твой уникальный ключ:</b>\n\n"
        f"<code>{key}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"📥 <b>Скачать чит:</b>\n"
        f"{DOWNLOAD_LINK}\n\n"
        f"📌 Инструкция в канале: {CHANNEL_LINK}\n\n"
        "⚠️ Ключ одноразовый — никому не передавай!"
    )

    try:
        await bot.send_message(
            user_id, key_message, parse_mode="HTML"
        )
        await message.answer(
            f"✅ Ключ выдан!\n"
            f"🔑 <code>{key}</code>",
            reply_markup=kb_admin(), parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка: {e}\nКлюч: <code>{key}</code>",
            reply_markup=kb_admin(), parse_mode="HTML"
        )

    await state.clear()


# --- Рассылка ---
@dp.callback_query(F.data == "a_broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    user_ids = await get_all_user_ids()
    try:
        await callback.message.edit_text(
            f"📢 <b>Рассылка</b>\n\n"
            f"Получателей: <b>{len(user_ids)}</b>\n\n"
            f"Отправь сообщение для рассылки.\n"
            f"Поддерживается HTML-разметка.",
            reply_markup=kb_cancel(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "Отправь сообщение для рассылки:",
            reply_markup=kb_cancel()
        )
    await state.set_state(AdminState.waiting_broadcast)
    await callback.answer()


@dp.message(AdminState.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = message.text or message.caption or ""
    if not text:
        await message.answer("Пустое сообщение.")
        return

    user_ids = await get_all_user_ids()
    success = 0
    failed = 0

    status_msg = await message.answer(
        f"📤 Рассылка... 0/{len(user_ids)}"
    )

    for i, uid in enumerate(user_ids):
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1

        if (i + 1) % 25 == 0:
            try:
                await status_msg.edit_text(
                    f"📤 Рассылка... {i + 1}/{len(user_ids)}\n"
                    f"✅ {success}  ❌ {failed}"
                )
            except Exception:
                pass
            await asyncio.sleep(0.5)

    await log_admin_action(
        message.from_user.id, "broadcast",
        details=f"success={success}, failed={failed}"
    )

    try:
        await status_msg.edit_text(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"📬 Доставлено: <b>{success}</b>\n"
            f"❌ Не доставлено: <b>{failed}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await state.clear()


# --- Бан ---
@dp.callback_query(F.data == "a_ban")
async def cb_ban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            "🚫 Отправь <b>ID пользователя</b> для бана:",
            reply_markup=kb_cancel(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "Отправь ID для бана:", reply_markup=kb_cancel()
        )
    await state.set_state(AdminState.waiting_ban_id)
    await callback.answer()


@dp.message(AdminState.waiting_ban_id)
async def process_ban(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Отправь числовой ID.")
        return

    user = await get_user(uid)
    if not user:
        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=kb_admin()
        )
        await state.clear()
        return

    if uid in ADMIN_IDS:
        await message.answer(
            "❌ Нельзя забанить админа!",
            reply_markup=kb_admin()
        )
        await state.clear()
        return

    await ban_user(uid)
    await log_admin_action(
        message.from_user.id, "ban", target_id=uid
    )

    try:
        await bot.send_message(
            uid, "🚫 Ваш аккаунт заблокирован администратором."
        )
    except Exception:
        pass

    await message.answer(
        f"✅ <b>{user['full_name']}</b> ({uid}) забанен.",
        reply_markup=kb_admin(), parse_mode="HTML"
    )
    await state.clear()


# --- Разбан ---
@dp.callback_query(F.data == "a_unban")
async def cb_unban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            "✅ Отправь <b>ID пользователя</b> для разбана:",
            reply_markup=kb_cancel(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "Отправь ID для разбана:", reply_markup=kb_cancel()
        )
    await state.set_state(AdminState.waiting_unban_id)
    await callback.answer()


@dp.message(AdminState.waiting_unban_id)
async def process_unban(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Отправь числовой ID.")
        return

    user = await get_user(uid)
    if not user:
        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=kb_admin()
        )
        await state.clear()
        return

    await unban_user(uid)
    await log_admin_action(
        message.from_user.id, "unban", target_id=uid
    )

    try:
        await bot.send_message(
            uid, "✅ Ваш аккаунт разблокирован!"
        )
    except Exception:
        pass

    await message.answer(
        f"✅ <b>{user['full_name']}</b> ({uid}) разбанен.",
        reply_markup=kb_admin(), parse_mode="HTML"
    )
    await state.clear()


# --- Инфо юзера ---
@dp.callback_query(F.data == "a_user_info")
async def cb_user_info(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            "👤 Отправь <b>ID пользователя</b>:",
            reply_markup=kb_cancel(), parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            "Отправь ID:", reply_markup=kb_cancel()
        )
    await state.set_state(AdminState.waiting_user_info_id)
    await callback.answer()


@dp.message(AdminState.waiting_user_info_id)
async def process_user_info(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Отправь числовой ID.")
        return

    user = await get_user(uid)
    if not user:
        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=kb_admin()
        )
        await state.clear()
        return

    videos = await get_user_videos(uid)
    sc = {"pending": 0, "approved": 0, "rejected": 0}
    for v in videos:
        if v["status"] in sc:
            sc[v["status"]] += 1

    banned = "🚫 Да" if user["is_banned"] else "✅ Нет"
    completed = "✅ Да" if user["is_completed"] else "❌ Нет"

    key = await get_user_key(uid)
    key_line = (
        f"🔑 Ключ: <code>{key}</code>"
        if key else "🔑 Ключ: не выдан"
    )

    reg = format_datetime(user.get("registered_at"))
    bar = make_progress_bar(
        user["video_count"], REQUIRED_VIDEOS
    )

    text = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"📛 Имя: {user['full_name']}\n"
        f"👤 Username: @{user['username'] or '—'}\n"
        f"📅 Регистрация: {reg}\n\n"
        f"📊 <b>Прогресс:</b>\n"
        f"{bar} {user['video_count']}/{REQUIRED_VIDEOS}\n"
        f"├ Задание: {completed}\n"
        f"├ {key_line}\n"
        f"└ Бан: {banned}\n\n"
        f"📹 <b>Видео:</b>\n"
        f"├ 🕐 На проверке: {sc['pending']}\n"
        f"├ ✅ Принято: {sc['approved']}\n"
        f"└ ❌ Отклонено: {sc['rejected']}"
    )

    await message.answer(
        text, reply_markup=kb_admin(), parse_mode="HTML"
    )
    await state.clear()


# ================== ЗАПУСК ==================
async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="admin", description="🔐 Админ-панель"),
    ]
    await bot.set_my_commands(commands)


async def main():
    await init_db()
    await set_bot_commands()

    logger.info("=" * 50)
    logger.info("🤖 Бот запущен!")
    logger.info(f"📱 Админы: {ADMIN_IDS}")
    logger.info(f"📹 Требуется видео: {REQUIRED_VIDEOS}")
    logger.info(f"📥 Ссылка скачивания: {DOWNLOAD_LINK}")
    logger.info(f"⏱ Кулдаун: {COOLDOWN_SECONDS} сек")
    logger.info("=" * 50)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
