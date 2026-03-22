import asyncio
import logging
import re
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
ADMIN_IDS = [8346538289]  # Список админов — можно несколько
REQUIRED_VIDEOS = 10
COOLDOWN_SECONDS = 10  # Защита от спама
DB_PATH = "users_data.db"
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

VIDEO_DESCRIPTION = """⚡️КАК СКАЧАТЬ ЧИТ 0.37.1 STANDOFF 2 БЕЗ РУТ И БАНА ПОЛНАЯ УСТАНОВКА

👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft
👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft

#standoff2 #стандофф2 #чит #standoff2чит #стандофф2чит"""

COMMENT_TEXT = "👉 СКАЧАТЬ ТУТ ТГК: https://t.me/AimNooBsoft"

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
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)


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
            CREATE TABLE IF NOT EXISTS admin_messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER,
                message   TEXT,
                sent_at   TEXT
            )
        """)
        await db.commit()
    logger.info("Database initialized")


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
                (user_id, username, full_name, datetime.now().isoformat())
            )
        else:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? "
                "WHERE user_id = ?",
                (username, full_name, user_id)
            )
        await db.commit()


async def add_video(user_id: int, video_url: str) -> tuple[bool, int]:
    """Добавить видео. Возвращает (is_completed, new_count)."""
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
            "SELECT video_count FROM users WHERE user_id = ?", (user_id,)
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
    """Проверяет кулдаун. Возвращает оставшиеся секунды или 0."""
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
            "SELECT id FROM videos WHERE user_id = ? AND video_url = ?",
            (user_id, url)
        ) as cur:
            return await cur.fetchone() is not None


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
            "UPDATE videos SET status = ?, reviewed_at = ? WHERE id = ?",
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
            "UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def mark_key_issued(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET key_issued = 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def get_statistics() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            stats["total_users"] = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_completed = 1"
        ) as c:
            stats["completed_users"] = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE key_issued = 1"
        ) as c:
            stats["keys_issued"] = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned = 1"
        ) as c:
            stats["banned_users"] = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM videos") as c:
            stats["total_videos"] = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM videos WHERE status = 'pending'"
        ) as c:
            stats["pending_videos"] = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM videos WHERE status = 'approved'"
        ) as c:
            stats["approved_videos"] = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM videos WHERE status = 'rejected'"
        ) as c:
            stats["rejected_videos"] = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE registered_at >= ?",
            (
                (datetime.now() - timedelta(hours=24)).isoformat(),
            )
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
            "WHERE is_completed = 1 AND key_issued = 0 AND is_banned = 0 "
            "ORDER BY completed_at ASC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_user_videos(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM videos WHERE user_id = ? ORDER BY submitted_at ASC",
            (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ================== СОСТОЯНИЯ FSM ==================
class VideoState(StatesGroup):
    waiting_for_link = State()


class AdminState(StatesGroup):
    waiting_broadcast = State()
    waiting_message_to_user = State()
    waiting_ban_id = State()
    waiting_unban_id = State()
    waiting_custom_key = State()


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
             text="📢 Рассылка", callback_data="a_broadcast"
         )],
        [InlineKeyboardButton(
            text="🚫 Бан", callback_data="a_ban"
        ),
         InlineKeyboardButton(
             text="✅ Разбан", callback_data="a_unban"
         )],
        [InlineKeyboardButton(
            text="👤 Инфо о юзере", callback_data="a_user_info"
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
            text="⬅️", callback_data=f"a_nav_{offset - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"{offset + 1}/{total}", callback_data="noop"
    ))
    if offset < total - 1:
        nav.append(InlineKeyboardButton(
            text="➡️", callback_data=f"a_nav_{offset + 1}"
        ))

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Принять", callback_data=f"approve_{video_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить", callback_data=f"reject_{video_id}"
            )
        ],
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


# ================== ОБРАБОТЧИКИ ==================

# --- /start ---
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    uname = message.from_user.username or "—"
    fname = message.from_user.full_name

    await register_user(uid, uname, fname)
    user = await get_user(uid)

    if user and user["is_banned"]:
        await message.answer("🚫 Ваш аккаунт заблокирован.")
        return

    bar = make_progress_bar(
        user["video_count"] if user else 0, REQUIRED_VIDEOS
    )
    count = user["video_count"] if user else 0

    text = (
        f"👋 <b>Привет, {fname}!</b>\n\n"
        f"Я помогу тебе получить чит Standoff 2 0.37.1\n\n"
        f"📊 Прогресс: {bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n\n"
        f"Выбери действие ниже 👇"
    )
    await message.answer(
        text, reply_markup=kb_main(uid), parse_mode="HTML"
    )


# --- /admin ---
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔐 <b>Админ-панель</b>",
        reply_markup=kb_admin(), parse_mode="HTML"
    )


# --- Меню ---
@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = callback.from_user.id
    user = await get_user(uid)
    count = user["video_count"] if user else 0
    bar = make_progress_bar(count, REQUIRED_VIDEOS)

    text = (
        f"🏠 <b>Главное меню</b>\n\n"
        f"📊 Прогресс: {bar} <b>{count}/{REQUIRED_VIDEOS}</b>"
    )
    await callback.message.edit_text(
        text, reply_markup=kb_main(uid), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.", reply_markup=kb_back_menu()
    )
    await callback.answer()


# --- Задание ---
@dp.callback_query(F.data == "task")
async def cb_task(callback: CallbackQuery):
    text = TASK_DESCRIPTION.format(required=REQUIRED_VIDEOS)
    await callback.message.edit_text(
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
        f"  <code>https://youtu.be/XXXXX</code> или\n"
        f"  <code>https://youtube.com/watch?v=XXXXX</code>\n\n"
        "▫️ <b>Сколько видео нужно?</b>\n"
        f"  {REQUIRED_VIDEOS} штук\n\n"
        "▫️ <b>Когда получу ключ?</b>\n"
        "  После проверки всех видео админом\n\n"
        "▫️ <b>Видео отклонили, что делать?</b>\n"
        "  Перечитай инструкцию и загрузи заново\n\n"
        "📩 По другим вопросам — пиши админу"
    )
    await callback.message.edit_text(
        text, reply_markup=kb_back_menu(), parse_mode="HTML"
    )
    await callback.answer()


# --- Данные для видео ---
@dp.callback_query(F.data == "data_menu")
async def cb_data_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📝 <b>Данные для видео</b>\n\n"
        "Выбери, что скопировать:",
        reply_markup=kb_data_menu(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "d_title")
async def cb_title(callback: CallbackQuery):
    await callback.message.edit_text(
        f"📝 <b>Название видео:</b>\n\n"
        f"<code>{VIDEO_TITLE}</code>\n\n"
        f"👆 Нажми, чтобы скопировать",
        reply_markup=kb_data_menu(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "d_desc")
async def cb_desc(callback: CallbackQuery):
    await callback.message.edit_text(
        f"📄 <b>Описание видео:</b>\n\n"
        f"<code>{VIDEO_DESCRIPTION}</code>\n\n"
        f"👆 Нажми, чтобы скопировать",
        reply_markup=kb_data_menu(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "d_comment")
async def cb_comment(callback: CallbackQuery):
    await callback.message.edit_text(
        f"💬 <b>Комментарий:</b>\n\n"
        f"<code>{COMMENT_TEXT}</code>\n\n"
        f"⚠️ <b>Обязательно</b> оставь этот комментарий!\n"
        f"Без него выдачи не будет.",
        reply_markup=kb_data_menu(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "d_tags")
async def cb_tags(callback: CallbackQuery):
    # Теги могут быть длинными — отправляем отдельным сообщением
    await callback.message.edit_text(
        "🏷 <b>Теги:</b>\n\n"
        f"<code>{TAGS[:3500]}</code>\n\n"
        "👆 Нажми, чтобы скопировать\n"
        "Вставь в описание видео",
        reply_markup=kb_data_menu(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "d_all")
async def cb_all_data(callback: CallbackQuery):
    text = (
        "📋 <b>ВСЕ ДАННЫЕ</b>\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Название:</b>\n<code>{VIDEO_TITLE}</code>\n\n"
        f"📄 <b>Описание:</b>\n<code>{VIDEO_DESCRIPTION}</code>\n\n"
        f"💬 <b>Комментарий:</b>\n<code>{COMMENT_TEXT}</code>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "Нажимай на тексты для копирования ☝️"
    )
    # Если слишком длинный — отправим новым сообщением
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

    text = (
        f"📊 <b>Твой прогресс</b>\n\n"
        f"{bar}\n"
        f"<b>{count} / {REQUIRED_VIDEOS} видео</b>\n\n"
        f"📌 Статус: {status}\n"
        f"📅 Регистрация: {reg}"
    )
    await callback.message.edit_text(
        text, reply_markup=kb_back_menu(), parse_mode="HTML"
    )
    await callback.answer()


# --- Мои видео ---
@dp.callback_query(F.data == "my_videos")
async def cb_my_videos(callback: CallbackQuery):
    uid = callback.from_user.id
    videos = await get_user_videos(uid)

    if not videos:
        await callback.message.edit_text(
            "📜 У тебя пока нет отправленных видео.",
            reply_markup=kb_back_menu()
        )
        await callback.answer()
        return

    status_emoji = {
        "pending": "🕐",
        "approved": "✅",
        "rejected": "❌"
    }
    status_text = {
        "pending": "На проверке",
        "approved": "Принято",
        "rejected": "Отклонено"
    }

    lines = ["📜 <b>Твои видео:</b>\n"]
    for i, v in enumerate(videos, 1):
        emoji = status_emoji.get(v["status"], "❓")
        st = status_text.get(v["status"], v["status"])
        dt = format_datetime(v["submitted_at"])
        lines.append(
            f"{i}. {emoji} {st}\n"
            f"   🔗 {v['video_url']}\n"
            f"   📅 {dt}\n"
        )

    text = "\n".join(lines)
    # Обрезаем если слишком длинный
    if len(text) > 4000:
        text = text[:4000] + "\n\n... и другие"

    await callback.message.edit_text(
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
        await callback.answer("🚫 Вы заблокированы", show_alert=True)
        return

    if user["key_issued"]:
        await callback.message.edit_text(
            "🎉 Ты уже получил ключ! Задание завершено.",
            reply_markup=kb_back_menu()
        )
        await callback.answer()
        return

    if user["video_count"] >= REQUIRED_VIDEOS:
        await callback.message.edit_text(
            f"✅ Все {REQUIRED_VIDEOS} видео отправлены!\n"
            "Ожидай проверки администратором.",
            reply_markup=kb_back_menu()
        )
        await callback.answer()
        return

    # Проверка кулдауна
    cd = await check_cooldown(uid)
    if cd > 0:
        await callback.answer(
            f"⏳ Подожди {cd} сек. перед следующей отправкой",
            show_alert=True
        )
        return

    count = user["video_count"]
    bar = make_progress_bar(count, REQUIRED_VIDEOS)

    await callback.message.edit_text(
        f"📤 <b>Отправка видео #{count + 1}</b>\n\n"
        f"{bar} <b>{count}/{REQUIRED_VIDEOS}</b>\n\n"
        f"Отправь ссылку на YouTube видео 👇\n\n"
        f"Форматы:\n"
        f"<code>https://youtu.be/XXXXX</code>\n"
        f"<code>https://youtube.com/watch?v=XXXXX</code>\n"
        f"<code>https://youtube.com/shorts/XXXXX</code>",
        reply_markup=kb_cancel(), parse_mode="HTML"
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

    # Валидация
    yt_pattern = (
        r'(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)'
        r'|youtu\.be/)[\w\-]+'
    )
    if not re.match(yt_pattern, url):
        await message.answer(
            "❌ <b>Неверная ссылка!</b>\n\n"
            "Допустимые форматы:\n"
            "<code>https://youtu.be/XXXXX</code>\n"
            "<code>https://youtube.com/watch?v=XXXXX</code>\n"
            "<code>https://youtube.com/shorts/XXXXX</code>\n\n"
            "Попробуй ещё раз 👇",
            parse_mode="HTML"
        )
        return

    # Дубликат
    if await check_duplicate_url(uid, url):
        await message.answer(
            "⚠️ Эта ссылка уже была отправлена! Отправь другую.",
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
            f"Ожидай — это обычно занимает до 24ч."
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
                    f"Отправлено {count} видео — пора проверять!",
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
    await callback.message.edit_text(
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
        f"🔑 Ключей выдано: <b>{s['keys_issued']}</b>\n"
        f"🚫 Забанено: <b>{s['banned_users']}</b>\n\n"
        f"📹 <b>Видео:</b>\n"
        f"├ Всего: <b>{s['total_videos']}</b>\n"
        f"├ 🕐 На проверке: <b>{s['pending_videos']}</b>\n"
        f"├ ✅ Принято: <b>{s['approved_videos']}</b>\n"
        f"└ ❌ Отклонено: <b>{s['rejected_videos']}</b>"
    )
    await callback.message.edit_text(
        text, reply_markup=kb_back_admin(), parse_mode="HTML"
    )
    await callback.answer()


# --- Проверка видео с пагинацией ---
@dp.callback_query(F.data == "a_check")
async def cb_check_videos(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    await state.update_data(review_offset=0)
    await show_review_page(callback, 0)


@dp.callback_query(F.data.startswith("a_nav_"))
async def cb_nav_review(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    offset = int(callback.data.split("_")[2])
    await show_review_page(callback, offset)


async def show_review_page(callback: CallbackQuery, offset: int):
    total = await count_pending_videos()
    if total == 0:
        await callback.message.edit_text(
            "📭 Нет видео на проверку!",
            reply_markup=kb_back_admin()
        )
        await callback.answer()
        return

    offset = min(offset, total - 1)
    videos = await get_pending_videos(offset=offset, limit=1)

    if not videos:
        await callback.message.edit_text(
            "📭 Нет видео на проверку!",
            reply_markup=kb_back_admin()
        )
        await callback.answer()
        return

    v = videos[0]
    dt = format_datetime(v["submitted_at"])

    text = (
        f"🔍 <b>Проверка видео</b>  ({offset + 1}/{total})\n\n"
        f"👤 <b>{v['full_name']}</b> (@{v['username'] or '—'})\n"
        f"🆔 <code>{v['user_id']}</code>\n"
        f"📊 Видео пользователя: {v['video_count']}/{REQUIRED_VIDEOS}\n"
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


@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    video_id = int(callback.data.split("_")[1])
    await update_video_status(video_id, "approved")
    user_id = await get_video_user_id(video_id)

    if user_id:
        try:
            await bot.send_message(
                user_id,
                "✅ Твоё видео одобрено! Продолжай в том же духе 💪"
            )
        except Exception:
            pass

    await callback.answer("✅ Видео одобрено!")
    # Показать следующее
    await show_review_page(callback, 0)


@dp.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    video_id = int(callback.data.split("_")[1])
    await update_video_status(video_id, "rejected")
    user_id = await get_video_user_id(video_id)

    if user_id:
        await decrement_video_count(user_id)
        try:
            user = await get_user(user_id)
            count = user["video_count"] if user else 0
            await bot.send_message(
                user_id,
                f"❌ <b>Видео отклонено!</b>\n\n"
                f"Причина: не соответствует требованиям.\n\n"
                f"📊 Текущий прогресс: {count}/{REQUIRED_VIDEOS}\n\n"
                f"Проверь:\n"
                f"• Видео без водяных знаков?\n"
                f"• Название верное?\n"
                f"• Описание верное?\n"
                f"• Комментарий оставлен?\n\n"
                f"Загрузи верное видео и отправь ссылку.",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer("❌ Видео отклонено!")
    await show_review_page(callback, 0)


# --- Выдача ключей ---
@dp.callback_query(F.data == "a_keys")
async def cb_keys_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    users = await get_completed_users()
    if not users:
        await callback.message.edit_text(
            "📭 Нет пользователей для выдачи ключа.",
            reply_markup=kb_back_admin()
        )
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
            callback_data=f"issue_key_{u['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Админ-панель", callback_data="admin_panel"
    )])

    await callback.message.edit_text(
        f"🎁 <b>Выдача ключей</b>\n\n"
        f"Готовы к выдаче: <b>{len(users)}</b> чел.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("issue_key_"))
async def cb_issue_key(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[2])
    await state.update_data(issue_user_id=user_id)

    user = await get_user(user_id)
    name = user["full_name"] if user else str(user_id)

    await callback.message.edit_text(
        f"🔑 Отправь ключ для <b>{name}</b>\n\n"
        f"Или отправь <code>default</code> для стандартного ключа.",
        reply_markup=kb_cancel(), parse_mode="HTML"
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
        await message.answer("Ошибка. Попробуй снова.")
        return

    key_text = message.text.strip()
    if key_text.lower() == "default":
        key_text = "STANDOFF2-2024-ACTIVE-KEY"

    key_message = (
        "🎉 <b>Поздравляю! Задание выполнено!</b>\n\n"
        "🔑 <b>Твой доступ:</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"<b>Чит Standoff 2 0.37.1</b>\n"
        f"<b>Ключ:</b> <code>{key_text}</code>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👉 <b>СКАЧАТЬ:</b> https://t.me/AimNooBsoft\n\n"
        "📌 Инструкция по установке в канале!"
    )

    try:
        await bot.send_message(
            user_id, key_message, parse_mode="HTML"
        )
        await mark_key_issued(user_id)
        await message.answer(
            f"✅ Ключ выдан пользователю {user_id}!",
            reply_markup=kb_admin()
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка отправки: {e}",
            reply_markup=kb_admin()
        )

    await state.clear()


# --- Рассылка ---
@dp.callback_query(F.data == "a_broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь сообщение для рассылки всем пользователям.\n"
        "Поддерживается HTML-разметка.",
        reply_markup=kb_cancel(), parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_broadcast)
    await callback.answer()


@dp.message(AdminState.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = message.text or message.caption or ""
    if not text:
        await message.answer("Пустое сообщение. Попробуй снова.")
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

        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(
                    f"📤 Рассылка... {i + 1}/{len(user_ids)}"
                )
            except Exception:
                pass
            await asyncio.sleep(0.5)

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📬 Доставлено: {success}\n"
        f"❌ Не доставлено: {failed}",
        parse_mode="HTML"
    )
    await state.clear()


# --- Бан ---
@dp.callback_query(F.data == "a_ban")
async def cb_ban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    await callback.message.edit_text(
        "🚫 Отправь <b>ID пользователя</b> для бана:",
        reply_markup=kb_cancel(), parse_mode="HTML"
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
        await message.answer("❌ Пользователь не найден.")
        return

    await ban_user(uid)
    try:
        await bot.send_message(uid, "🚫 Ваш аккаунт заблокирован.")
    except Exception:
        pass
    await message.answer(
        f"✅ Пользователь {user['full_name']} ({uid}) забанен.",
        reply_markup=kb_admin()
    )
    await state.clear()


# --- Разбан ---
@dp.callback_query(F.data == "a_unban")
async def cb_unban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    await callback.message.edit_text(
        "✅ Отправь <b>ID пользователя</b> для разбана:",
        reply_markup=kb_cancel(), parse_mode="HTML"
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
        await message.answer("❌ Пользователь не найден.")
        return

    await unban_user(uid)
    try:
        await bot.send_message(uid, "✅ Ваш аккаунт разблокирован!")
    except Exception:
        pass
    await message.answer(
        f"✅ Пользователь {user['full_name']} ({uid}) разбанен.",
        reply_markup=kb_admin()
    )
    await state.clear()


# --- Инфо о пользователе ---
@dp.callback_query(F.data == "a_user_info")
async def cb_user_info_prompt(
    callback: CallbackQuery, state: FSMContext
):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав!", show_alert=True)
        return
    await callback.message.edit_text(
        "👤 Отправь <b>ID пользователя</b>:",
        reply_markup=kb_cancel(), parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_message_to_user)
    await callback.answer()


@dp.message(AdminState.waiting_message_to_user)
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
            "❌ Пользователь не найден.", reply_markup=kb_admin()
        )
        await state.clear()
        return

    videos = await get_user_videos(uid)
    status_counts = {"pending": 0, "approved": 0, "rejected": 0}
    for v in videos:
        st = v["status"]
        if st in status_counts:
            status_counts[st] += 1

    banned = "🚫 Да" if user["is_banned"] else "✅ Нет"
    completed = "✅ Да" if user["is_completed"] else "❌ Нет"
    key = "🔑 Да" if user["key_issued"] else "❌ Нет"
    reg = format_datetime(user.get("registered_at"))

    text = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"📛 Имя: {user['full_name']}\n"
        f"👤 Username: @{user['username'] or '—'}\n"
        f"📅 Регистрация: {reg}\n\n"
        f"📊 <b>Прогресс:</b>\n"
        f"├ Видео: {user['video_count']}/{REQUIRED_VIDEOS}\n"
        f"├ Задание выполнено: {completed}\n"
        f"├ Ключ выдан: {key}\n"
        f"└ Забанен: {banned}\n\n"
        f"📹 <b>Видео:</b>\n"
        f"├ 🕐 На проверке: {status_counts['pending']}\n"
        f"├ ✅ Принято: {status_counts['approved']}\n"
        f"└ ❌ Отклонено: {status_counts['rejected']}"
    )

    await message.answer(text, reply_markup=kb_admin(), parse_mode="HTML")
    await state.clear()


# ================== SETUP ==================
async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="admin", description="🔐 Админ-панель"),
    ]
    await bot.set_my_commands(commands)


async def main():
    await init_db()
    await set_bot_commands()
    logger.info("🤖 Бот запущен!")
    logger.info(f"📱 Админы: {ADMIN_IDS}")
    logger.info(f"📹 Требуется видео: {REQUIRED_VIDEOS}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
