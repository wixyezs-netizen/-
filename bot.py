"""
Telegram Mini App для AimNoob Bot
Домен: AimMani.bothost.tech
Всё в одном файле: FastAPI backend + HTML/CSS/JS frontend
"""

import os
import json
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qs, unquote

import aiosqlite
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ================== КОНФИГУРАЦИЯ ==================
API_TOKEN = "8624719452:AAHBAWy6DDzXD_ekK-iI8_rAOj4lUr3PysA"
BOT_TOKEN = API_TOKEN
DB_PATH = "users_data.db"
REQUIRED_VIDEOS = 10
DOMAIN = "AimMani.bothost.tech"
CHANNEL_LINK = "https://t.me/AimNooBsoft"
DOWNLOAD_LINK = "https://go.linkify.ru/2GPF"

# ================== ДАННЫЕ ДЛЯ ВИДЕО ==================
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AimNoob Mini App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================== ВАЛИДАЦИЯ TELEGRAM ==================
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


# ================== DATABASE ==================
async def get_db():
    return await aiosqlite.connect(DB_PATH)


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


async def get_user_data(user_id: int) -> dict:
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
            "SELECT user_id, full_name, username, video_count, "
            "is_completed, key_issued FROM users "
            "WHERE is_banned = 0 AND video_count > 0 "
            "ORDER BY video_count DESC, registered_at ASC LIMIT 50"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ================== API ROUTES ==================
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

MINI_APP_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, 
          user-scalable=no, maximum-scale=1.0">
    <title>AimNoob | Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        /* ===== CSS RESET & VARIABLES ===== */
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a2e;
            --bg-card-hover: #1f1f35;
            --accent: #6c5ce7;
            --accent-light: #a29bfe;
            --accent-dark: #5a4bd1;
            --accent-glow: rgba(108, 92, 231, 0.3);
            --green: #00e676;
            --green-dark: #00c853;
            --green-glow: rgba(0, 230, 118, 0.2);
            --red: #ff5252;
            --red-glow: rgba(255, 82, 82, 0.2);
            --orange: #ffab40;
            --orange-glow: rgba(255, 171, 64, 0.2);
            --yellow: #ffd740;
            --cyan: #00e5ff;
            --cyan-glow: rgba(0, 229, 255, 0.15);
            --text-primary: #ffffff;
            --text-secondary: #a0a0b8;
            --text-muted: #6c6c80;
            --border: rgba(108, 92, 231, 0.15);
            --border-active: rgba(108, 92, 231, 0.4);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            --shadow-glow: 0 0 30px var(--accent-glow);
            --radius: 16px;
            --radius-sm: 10px;
            --radius-xs: 6px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                         'SF Pro Display', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            padding-bottom: 100px;
        }

        /* ===== ANIMATED BACKGROUND ===== */
        .bg-pattern {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: -1;
            overflow: hidden;
        }

        .bg-pattern::before {
            content: '';
            position: absolute;
            top: -50%; left: -50%;
            width: 200%; height: 200%;
            background:
                radial-gradient(
                    ellipse at 20% 50%,
                    rgba(108, 92, 231, 0.08) 0%,
                    transparent 50%
                ),
                radial-gradient(
                    ellipse at 80% 20%,
                    rgba(0, 229, 255, 0.05) 0%,
                    transparent 50%
                ),
                radial-gradient(
                    ellipse at 50% 80%,
                    rgba(0, 230, 118, 0.04) 0%,
                    transparent 50%
                );
            animation: bgFloat 20s ease-in-out infinite;
        }

        @keyframes bgFloat {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            33% { transform: translate(2%, -2%) rotate(1deg); }
            66% { transform: translate(-1%, 1%) rotate(-1deg); }
        }

        .floating-orb {
            position: fixed;
            border-radius: 50%;
            filter: blur(60px);
            opacity: 0.15;
            animation: orbFloat 15s ease-in-out infinite;
        }

        .orb-1 {
            width: 300px; height: 300px;
            background: var(--accent);
            top: -100px; right: -100px;
            animation-delay: 0s;
        }

        .orb-2 {
            width: 200px; height: 200px;
            background: var(--cyan);
            bottom: 20%; left: -50px;
            animation-delay: -5s;
        }

        .orb-3 {
            width: 250px; height: 250px;
            background: var(--green);
            top: 40%; right: -80px;
            animation-delay: -10s;
        }

        @keyframes orbFloat {
            0%, 100% { transform: translate(0, 0) scale(1); }
            25% { transform: translate(30px, -20px) scale(1.1); }
            50% { transform: translate(-20px, 30px) scale(0.9); }
            75% { transform: translate(10px, -10px) scale(1.05); }
        }

        /* ===== LOADING SCREEN ===== */
        .loading-screen {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: var(--bg-primary);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            transition: opacity 0.5s, visibility 0.5s;
        }

        .loading-screen.hidden {
            opacity: 0;
            visibility: hidden;
        }

        .loader-logo {
            font-size: 42px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent), var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 30px;
            animation: logoPulse 2s ease-in-out infinite;
        }

        @keyframes logoPulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.8; }
        }

        .loader-spinner {
            width: 50px; height: 50px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loader-text {
            margin-top: 20px;
            color: var(--text-secondary);
            font-size: 14px;
            animation: textPulse 1.5s ease-in-out infinite;
        }

        @keyframes textPulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }

        /* ===== HEADER ===== */
        .header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(10, 10, 15, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            padding: 16px 20px;
        }

        .header-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 600px;
            margin: 0 auto;
        }

        .header-logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo-icon {
            width: 36px; height: 36px;
            background: linear-gradient(135deg, var(--accent), var(--cyan));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            box-shadow: 0 0 15px var(--accent-glow);
        }

        .logo-text {
            font-size: 18px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--text-primary), var(--accent-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .header-user {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: var(--bg-card);
            border-radius: 20px;
            border: 1px solid var(--border);
        }

        .header-avatar {
            width: 28px; height: 28px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent), var(--green));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
        }

        .header-name {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            max-width: 100px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* ===== CONTAINER ===== */
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
        }

        /* ===== STATUS BANNER ===== */
        .status-banner {
            background: linear-gradient(135deg,
                rgba(108, 92, 231, 0.15),
                rgba(0, 229, 255, 0.1)
            );
            border: 1px solid var(--border-active);
            border-radius: var(--radius);
            padding: 20px;
            margin-bottom: 16px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .status-banner::before {
            content: '';
            position: absolute;
            top: 0; left: -100%;
            width: 200%; height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255,255,255,0.03),
                transparent
            );
            animation: shimmer 3s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-50%); }
            100% { transform: translateX(50%); }
        }

        .status-emoji {
            font-size: 36px;
            margin-bottom: 8px;
        }

        .status-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .status-subtitle {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .status-banner.completed {
            background: linear-gradient(135deg,
                rgba(0, 230, 118, 0.15),
                rgba(0, 229, 255, 0.1)
            );
            border-color: rgba(0, 230, 118, 0.3);
        }

        .status-banner.has-key {
            background: linear-gradient(135deg,
                rgba(255, 215, 64, 0.15),
                rgba(255, 171, 64, 0.1)
            );
            border-color: rgba(255, 215, 64, 0.3);
        }

        .status-banner.banned {
            background: linear-gradient(135deg,
                rgba(255, 82, 82, 0.15),
                rgba(255, 82, 82, 0.1)
            );
            border-color: rgba(255, 82, 82, 0.3);
        }

        /* ===== PROGRESS SECTION ===== */
        .progress-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            margin-bottom: 16px;
        }

        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
        }

        .progress-label {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .progress-count {
            font-size: 20px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-light), var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .progress-bar-container {
            width: 100%;
            height: 12px;
            background: rgba(108, 92, 231, 0.1);
            border-radius: 6px;
            overflow: hidden;
            position: relative;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--cyan));
            border-radius: 6px;
            transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            min-width: 0%;
        }

        .progress-bar-fill::after {
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255,255,255,0.2) 50%,
                transparent 100%
            );
            animation: progressShimmer 2s infinite;
        }

        @keyframes progressShimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .progress-steps {
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
        }

        .progress-step {
            width: 24px; height: 24px;
            border-radius: 50%;
            background: var(--bg-secondary);
            border: 2px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 700;
            color: var(--text-muted);
            transition: var(--transition);
        }

        .progress-step.done {
            background: var(--accent);
            border-color: var(--accent);
            color: #fff;
            box-shadow: 0 0 10px var(--accent-glow);
        }

        .progress-step.current {
            border-color: var(--cyan);
            color: var(--cyan);
            animation: stepPulse 2s infinite;
        }

        @keyframes stepPulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.3); }
            50% { box-shadow: 0 0 0 6px rgba(0, 229, 255, 0); }
        }

        /* ===== NAV TABS ===== */
        .nav-tabs {
            display: flex;
            gap: 6px;
            margin-bottom: 16px;
            padding: 4px;
            background: var(--bg-card);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }

        .nav-tabs::-webkit-scrollbar {
            display: none;
        }

        .nav-tab {
            flex: 1;
            min-width: 0;
            padding: 10px 8px;
            border-radius: 12px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
        }

        .nav-tab .tab-icon {
            font-size: 18px;
        }

        .nav-tab.active {
            background: var(--accent);
            color: #fff;
            box-shadow: 0 4px 15px var(--accent-glow);
        }

        .nav-tab:not(.active):hover {
            background: rgba(108, 92, 231, 0.1);
            color: var(--text-secondary);
        }

        /* ===== SECTIONS ===== */
        .section {
            display: none;
            animation: fadeInUp 0.4s ease;
        }

        .section.active {
            display: block;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(15px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* ===== CARDS ===== */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 18px;
            margin-bottom: 12px;
            transition: var(--transition);
        }

        .card:hover {
            border-color: var(--border-active);
            background: var(--bg-card-hover);
        }

        .card-title {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-text {
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.6;
        }

        /* ===== COPY BLOCKS ===== */
        .copy-block {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 14px;
            margin: 10px 0;
            position: relative;
            cursor: pointer;
            transition: var(--transition);
        }

        .copy-block:active {
            transform: scale(0.98);
        }

        .copy-block:hover {
            border-color: var(--accent);
        }

        .copy-block-label {
            font-size: 11px;
            color: var(--accent-light);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }

        .copy-block-text {
            font-size: 12px;
            color: var(--text-primary);
            line-height: 1.5;
            word-break: break-all;
            font-family: 'SF Mono', 'Fira Code', monospace;
        }

        .copy-btn {
            position: absolute;
            top: 10px; right: 10px;
            background: var(--accent);
            border: none;
            border-radius: 8px;
            padding: 6px 12px;
            color: #fff;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .copy-btn:hover {
            background: var(--accent-dark);
            transform: scale(1.05);
        }

        .copy-btn.copied {
            background: var(--green);
        }

        /* ===== KEY DISPLAY ===== */
        .key-display {
            background: linear-gradient(135deg,
                rgba(255, 215, 64, 0.1),
                rgba(108, 92, 231, 0.1)
            );
            border: 2px solid rgba(255, 215, 64, 0.3);
            border-radius: var(--radius);
            padding: 24px;
            text-align: center;
            margin: 16px 0;
            position: relative;
            overflow: hidden;
        }

        .key-display::before {
            content: '';
            position: absolute;
            top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: conic-gradient(
                from 0deg,
                transparent,
                rgba(255, 215, 64, 0.05),
                transparent,
                rgba(108, 92, 231, 0.05),
                transparent
            );
            animation: keyRotate 10s linear infinite;
        }

        @keyframes keyRotate {
            to { transform: rotate(360deg); }
        }

        .key-icon {
            font-size: 48px;
            margin-bottom: 12px;
            animation: keyBounce 2s ease-in-out infinite;
        }

        @keyframes keyBounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
        }

        .key-value {
            font-size: 18px;
            font-weight: 800;
            font-family: 'SF Mono', 'Fira Code', monospace;
            color: var(--yellow);
            letter-spacing: 2px;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
            display: inline-block;
            margin: 8px 0;
            position: relative;
            z-index: 1;
            cursor: pointer;
            transition: var(--transition);
        }

        .key-value:hover {
            transform: scale(1.02);
        }

        /* ===== VIDEO LIST ===== */
        .video-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            margin-bottom: 8px;
            transition: var(--transition);
        }

        .video-item:hover {
            border-color: var(--border-active);
        }

        .video-number {
            width: 32px; height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 700;
            flex-shrink: 0;
        }

        .video-number.pending {
            background: rgba(255, 171, 64, 0.15);
            color: var(--orange);
            border: 1px solid rgba(255, 171, 64, 0.3);
        }

        .video-number.approved {
            background: var(--green-glow);
            color: var(--green);
            border: 1px solid rgba(0, 230, 118, 0.3);
        }

        .video-number.rejected {
            background: var(--red-glow);
            color: var(--red);
            border: 1px solid rgba(255, 82, 82, 0.3);
        }

        .video-info {
            flex: 1;
            min-width: 0;
        }

        .video-url {
            font-size: 12px;
            color: var(--accent-light);
            text-decoration: none;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: block;
        }

        .video-date {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .video-status {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 20px;
            flex-shrink: 0;
        }

        .video-status.pending {
            background: var(--orange-glow);
            color: var(--orange);
        }

        .video-status.approved {
            background: var(--green-glow);
            color: var(--green);
        }

        .video-status.rejected {
            background: var(--red-glow);
            color: var(--red);
        }

        /* ===== LEADERBOARD ===== */
        .leader-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            margin-bottom: 8px;
            transition: var(--transition);
        }

        .leader-item.top-1 {
            border-color: rgba(255, 215, 64, 0.4);
            background: rgba(255, 215, 64, 0.05);
        }

        .leader-item.top-2 {
            border-color: rgba(192, 192, 192, 0.3);
            background: rgba(192, 192, 192, 0.03);
        }

        .leader-item.top-3 {
            border-color: rgba(205, 127, 50, 0.3);
            background: rgba(205, 127, 50, 0.03);
        }

        .leader-rank {
            width: 32px; height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 800;
            flex-shrink: 0;
        }

        .leader-info {
            flex: 1;
            min-width: 0;
        }

        .leader-name {
            font-size: 14px;
            font-weight: 600;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .leader-username {
            font-size: 11px;
            color: var(--text-muted);
        }

        .leader-score {
            font-size: 14px;
            font-weight: 700;
            color: var(--accent-light);
            flex-shrink: 0;
        }

        .leader-badge {
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 10px;
            font-weight: 600;
            flex-shrink: 0;
        }

        .leader-badge.completed {
            background: var(--green-glow);
            color: var(--green);
        }

        .leader-badge.key {
            background: rgba(255, 215, 64, 0.15);
            color: var(--yellow);
        }

        /* ===== STATS GRID ===== */
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
            text-align: center;
            transition: var(--transition);
        }

        .stat-card:hover {
            border-color: var(--border-active);
            transform: translateY(-2px);
        }

        .stat-icon {
            font-size: 24px;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-light), var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }

        /* ===== INSTRUCTION STEPS ===== */
        .step {
            display: flex;
            gap: 14px;
            margin-bottom: 16px;
        }

        .step-indicator {
            display: flex;
            flex-direction: column;
            align-items: center;
            flex-shrink: 0;
        }

        .step-number {
            width: 36px; height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent), var(--accent-dark));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 800;
            color: #fff;
            box-shadow: 0 0 15px var(--accent-glow);
        }

        .step-line {
            width: 2px;
            flex: 1;
            background: linear-gradient(
                to bottom,
                var(--accent),
                transparent
            );
            margin-top: 6px;
        }

        .step-content {
            padding-top: 6px;
        }

        .step-title {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .step-desc {
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.6;
        }

        /* ===== ACTION BUTTON ===== */
        .action-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            padding: 14px 20px;
            border-radius: var(--radius-sm);
            border: none;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: var(--transition);
            margin-top: 12px;
        }

        .action-btn.primary {
            background: linear-gradient(135deg, var(--accent), var(--accent-dark));
            color: #fff;
            box-shadow: 0 4px 20px var(--accent-glow);
        }

        .action-btn.primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px var(--accent-glow);
        }

        .action-btn.primary:active {
            transform: scale(0.98);
        }

        .action-btn.success {
            background: linear-gradient(135deg, var(--green), var(--green-dark));
            color: #fff;
            box-shadow: 0 4px 20px var(--green-glow);
        }

        .action-btn.outline {
            background: transparent;
            border: 1px solid var(--border-active);
            color: var(--accent-light);
        }

        .action-btn.outline:hover {
            background: rgba(108, 92, 231, 0.1);
        }

        /* ===== DOWNLOAD SECTION ===== */
        .download-section {
            background: linear-gradient(135deg,
                rgba(0, 230, 118, 0.1),
                rgba(0, 229, 255, 0.08)
            );
            border: 1px solid rgba(0, 230, 118, 0.2);
            border-radius: var(--radius);
            padding: 20px;
            text-align: center;
            margin: 16px 0;
        }

        .download-icon {
            font-size: 40px;
            margin-bottom: 8px;
        }

        .download-title {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .download-desc {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }

        /* ===== EMPTY STATE ===== */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-muted);
        }

        .empty-icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }

        .empty-text {
            font-size: 14px;
        }

        /* ===== TOAST ===== */
        .toast {
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: var(--bg-card);
            border: 1px solid var(--accent);
            border-radius: 12px;
            padding: 12px 20px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-primary);
            z-index: 1000;
            transition: transform 0.3s ease;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }

        .toast.success {
            border-color: var(--green);
        }

        /* ===== SECTION TITLE ===== */
        .section-title {
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .section-title .title-icon {
            font-size: 22px;
        }

        /* ===== DIVIDER ===== */
        .divider {
            width: 100%;
            height: 1px;
            background: var(--border);
            margin: 16px 0;
        }

        /* ===== WARNING ===== */
        .warning-box {
            background: rgba(255, 171, 64, 0.1);
            border: 1px solid rgba(255, 171, 64, 0.3);
            border-radius: var(--radius-sm);
            padding: 12px 14px;
            font-size: 12px;
            color: var(--orange);
            display: flex;
            align-items: flex-start;
            gap: 8px;
            margin: 12px 0;
        }

        .warning-box .warn-icon {
            font-size: 16px;
            flex-shrink: 0;
            margin-top: 1px;
        }

        /* ===== BOTTOM NAV (optional extra) ===== */
        .bottom-spacer {
            height: 30px;
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 380px) {
            .container {
                padding: 12px;
            }
            .stats-grid {
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }
            .nav-tab {
                font-size: 11px;
                padding: 8px 6px;
            }
        }
    </style>
</head>
<body>
    <!-- Background -->
    <div class="bg-pattern"></div>
    <div class="floating-orb orb-1"></div>
    <div class="floating-orb orb-2"></div>
    <div class="floating-orb orb-3"></div>

    <!-- Loading Screen -->
    <div class="loading-screen" id="loadingScreen">
        <div class="loader-logo">AIMNOOB</div>
        <div class="loader-spinner"></div>
        <div class="loader-text">Загрузка данных...</div>
    </div>

    <!-- Header -->
    <div class="header">
        <div class="header-inner">
            <div class="header-logo">
                <div class="logo-icon">⚡</div>
                <span class="logo-text">AimNoob</span>
            </div>
            <div class="header-user" id="headerUser">
                <div class="header-avatar" id="headerAvatar">?</div>
                <span class="header-name" id="headerName">User</span>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Status Banner -->
        <div class="status-banner" id="statusBanner">
            <div class="status-emoji" id="statusEmoji">🎮</div>
            <div class="status-title" id="statusTitle">Загрузка...</div>
            <div class="status-subtitle" id="statusSubtitle">Получение данных</div>
        </div>

        <!-- Progress -->
        <div class="progress-section" id="progressSection">
            <div class="progress-header">
                <span class="progress-label">Прогресс задания</span>
                <span class="progress-count" id="progressCount">0/""" + str(REQUIRED_VIDEOS) + """</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" id="progressBar" style="width: 0%"></div>
            </div>
            <div class="progress-steps" id="progressSteps"></div>
        </div>

        <!-- Navigation Tabs -->
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('task')" id="tabTask">
                <span class="tab-icon">📋</span>
                Задание
            </button>
            <button class="nav-tab" onclick="switchTab('data')" id="tabData">
                <span class="tab-icon">📝</span>
                Данные
            </button>
            <button class="nav-tab" onclick="switchTab('videos')" id="tabVideos">
                <span class="tab-icon">📹</span>
                Видео
            </button>
            <button class="nav-tab" onclick="switchTab('key')" id="tabKey">
                <span class="tab-icon">🔑</span>
                Ключ
            </button>
            <button class="nav-tab" onclick="switchTab('top')" id="tabTop">
                <span class="tab-icon">🏆</span>
                Топ
            </button>
        </div>

        <!-- SECTION: Task -->
        <div class="section active" id="sectionTask">
            <div class="section-title">
                <span class="title-icon">📋</span>
                Инструкция
            </div>

            <div class="step">
                <div class="step-indicator">
                    <div class="step-number">1</div>
                    <div class="step-line"></div>
                </div>
                <div class="step-content">
                    <div class="step-title">Найди видео</div>
                    <div class="step-desc">
                        Берёшь видео с TikTok из Telegram-каналов.
                        Тематика: чит Standoff 2 0.37.1.
                        Видео должны быть <b>БЕЗ</b> водяных знаков.
                    </div>
                </div>
            </div>

            <div class="step">
                <div class="step-indicator">
                    <div class="step-number">2</div>
                    <div class="step-line"></div>
                </div>
                <div class="step-content">
                    <div class="step-title">Выложи на YouTube</div>
                    <div class="step-desc">
                        Загружаешь как <b>обычный</b> ролик (НЕ Shorts).
                        Вставляешь название и описание из раздела «Данные».
                        В комментариях — ссылку на ТГ-канал.
                    </div>
                </div>
            </div>

            <div class="step">
                <div class="step-indicator">
                    <div class="step-number">3</div>
                    <div class="step-line"></div>
                </div>
                <div class="step-content">
                    <div class="step-title">Отправь ссылку</div>
                    <div class="step-desc">
                        Отправь ссылку на загруженное видео боту.
                        Повтори """ + str(REQUIRED_VIDEOS) + """ раз.
                        После проверки — получишь ключ!
                    </div>
                </div>
            </div>

            <div class="warning-box">
                <span class="warn-icon">⚠️</span>
                <span>Без ссылки в комментариях на ТГ-канал выдачи не будет! Это обязательное условие.</span>
            </div>

            <button class="action-btn primary" onclick="openBot()">
                📤 Отправить ссылку боту
            </button>
        </div>

        <!-- SECTION: Data -->
        <div class="section" id="sectionData">
            <div class="section-title">
                <span class="title-icon">📝</span>
                Данные для видео
            </div>

            <div class="copy-block" onclick="copyText('titleText', this)">
                <div class="copy-block-label">📝 Название</div>
                <div class="copy-block-text" id="titleText">""" + VIDEO_TITLE + """</div>
                <button class="copy-btn">📋 Копировать</button>
            </div>

            <div class="copy-block" onclick="copyText('descText', this)">
                <div class="copy-block-label">📄 Описание</div>
                <div class="copy-block-text" id="descText">""" + VIDEO_DESCRIPTION.replace('\n', '<br>') + """</div>
                <button class="copy-btn">📋 Копировать</button>
            </div>

            <div class="copy-block" onclick="copyText('commentText', this)">
                <div class="copy-block-label">💬 Комментарий</div>
                <div class="copy-block-text" id="commentText">""" + COMMENT_TEXT + """</div>
                <button class="copy-btn">📋 Копировать</button>
            </div>

            <div class="copy-block" onclick="copyText('tagsText', this)">
                <div class="copy-block-label">🏷 Теги</div>
                <div class="copy-block-text" id="tagsText" style="max-height:100px;overflow:hidden;">""" + TAGS[:500] + """...</div>
                <button class="copy-btn">📋 Копировать</button>
            </div>

            <div class="warning-box">
                <span class="warn-icon">💡</span>
                <span>Нажми на блок чтобы скопировать текст</span>
            </div>
        </div>

        <!-- SECTION: Videos -->
        <div class="section" id="sectionVideos">
            <div class="section-title">
                <span class="title-icon">📹</span>
                Мои видео
            </div>
            <div id="videosList">
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <div class="empty-text">Видео пока нет</div>
                </div>
            </div>
        </div>

        <!-- SECTION: Key -->
        <div class="section" id="sectionKey">
            <div class="section-title">
                <span class="title-icon">🔑</span>
                Мой ключ
            </div>
            <div id="keyContent">
                <div class="empty-state">
                    <div class="empty-icon">🔒</div>
                    <div class="empty-text">Ключ ещё не получен</div>
                </div>
            </div>
        </div>

        <!-- SECTION: Leaderboard -->
        <div class="section" id="sectionTop">
            <div class="section-title">
                <span class="title-icon">🏆</span>
                Таблица лидеров
            </div>
            <div id="leaderboardList">
                <div class="empty-state">
                    <div class="empty-icon">📊</div>
                    <div class="empty-text">Загрузка...</div>
                </div>
            </div>
        </div>

        <div class="bottom-spacer"></div>
    </div>

    <!-- Toast -->
    <div class="toast" id="toast">
        <span id="toastIcon">✅</span>
        <span id="toastText">Скопировано!</span>
    </div>

    <script>
        // ===== GLOBALS =====
        const REQUIRED = """ + str(REQUIRED_VIDEOS) + """;
        const CHANNEL = '""" + CHANNEL_LINK + """';
        const DOWNLOAD = '""" + DOWNLOAD_LINK + """';
        const FULL_TAGS = `""" + TAGS + """`;
        const FULL_DESC = `""" + VIDEO_DESCRIPTION + """`;
        const API_BASE = '';

        let tg = window.Telegram?.WebApp;
        let userData = null;
        let userId = null;

        // ===== INIT =====
        document.addEventListener('DOMContentLoaded', async () => {
            if (tg) {
                tg.ready();
                tg.expand();
                tg.setHeaderColor('#0a0a0f');
                tg.setBackgroundColor('#0a0a0f');

                if (tg.initDataUnsafe?.user) {
                    userId = tg.initDataUnsafe.user.id;
                    const name = tg.initDataUnsafe.user.first_name || 'User';
                    document.getElementById('headerName').textContent = name;
                    document.getElementById('headerAvatar').textContent =
                        name.charAt(0).toUpperCase();
                }
            }

            // Fallback: get userId from URL params
            if (!userId) {
                const params = new URLSearchParams(window.location.search);
                userId = params.get('user_id') || null;
            }

            if (userId) {
                await loadUserData();
            } else {
                hideLoading();
                updateStatus('error', '❌', 'Ошибка', 'Откройте через Telegram бот');
            }
        });

        // ===== LOAD DATA =====
        async function loadUserData() {
            try {
                const res = await fetch(`${API_BASE}/api/user/${userId}`);
                if (!res.ok) throw new Error('User not found');
                userData = await res.json();
                renderAll();
            } catch (e) {
                console.error(e);
                updateStatus('', '🆕', 'Начни задание',
                    'Отправь /start боту');
                renderAll();
            } finally {
                hideLoading();
            }
        }

        function hideLoading() {
            setTimeout(() => {
                document.getElementById('loadingScreen').classList.add('hidden');
            }, 600);
        }

        // ===== RENDER =====
        function renderAll() {
            renderStatus();
            renderProgress();
            renderVideos();
            renderKey();
            loadLeaderboard();
        }

        function renderStatus() {
            if (!userData) return;

            const banner = document.getElementById('statusBanner');
            banner.className = 'status-banner';

            if (userData.is_banned) {
                updateStatus('banned', '🚫', 'Аккаунт заблокирован',
                    'Обратитесь к администратору');
            } else if (userData.key_issued && userData.key) {
                updateStatus('has-key', '🎉', 'Ключ получен!',
                    'Скачай чит и активируй');
            } else if (userData.is_completed) {
                updateStatus('completed', '✅', 'Задание выполнено!',
                    'Ожидай проверки администратором');
            } else if (userData.video_count > 0) {
                const left = REQUIRED - userData.video_count;
                updateStatus('', '⏳', 'В процессе',
                    `Осталось ${left} видео`);
            } else {
                updateStatus('', '🎮', 'Добро пожаловать!',
                    'Выполни задание и получи чит');
            }
        }

        function updateStatus(cls, emoji, title, subtitle) {
            const banner = document.getElementById('statusBanner');
            if (cls) banner.classList.add(cls);
            document.getElementById('statusEmoji').textContent = emoji;
            document.getElementById('statusTitle').textContent = title;
            document.getElementById('statusSubtitle').textContent = subtitle;
        }

        function renderProgress() {
            const count = userData?.video_count || 0;
            const pct = Math.min(100, (count / REQUIRED) * 100);

            document.getElementById('progressCount').textContent =
                `${count}/${REQUIRED}`;
            document.getElementById('progressBar').style.width = `${pct}%`;

            // Steps
            const stepsEl = document.getElementById('progressSteps');
            stepsEl.innerHTML = '';

            const stepCount = Math.min(REQUIRED, 10);
            const stepSize = REQUIRED / stepCount;

            for (let i = 1; i <= stepCount; i++) {
                const threshold = Math.ceil(stepSize * i);
                const step = document.createElement('div');
                step.className = 'progress-step';

                if (count >= threshold) {
                    step.classList.add('done');
                    step.textContent = '✓';
                } else if (count >= threshold - stepSize) {
                    step.classList.add('current');
                    step.textContent = threshold;
                } else {
                    step.textContent = threshold;
                }

                stepsEl.appendChild(step);
            }
        }

        function renderVideos() {
            const container = document.getElementById('videosList');
            const videos = userData?.videos || [];

            if (videos.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">📭</div>
                        <div class="empty-text">Ты ещё не отправлял видео</div>
                    </div>
                    <button class="action-btn primary" onclick="openBot()">
                        📤 Отправить первое видео
                    </button>
                `;
                return;
            }

            const statusLabels = {
                pending: 'На проверке',
                approved: 'Принято',
                rejected: 'Отклонено'
            };

            let html = '';
            videos.forEach((v, i) => {
                const date = v.submitted_at ?
                    new Date(v.submitted_at).toLocaleDateString('ru-RU', {
                        day: '2-digit', month: '2-digit',
                        hour: '2-digit', minute: '2-digit'
                    }) : '—';

                html += `
                    <div class="video-item">
                        <div class="video-number ${v.status}">${i + 1}</div>
                        <div class="video-info">
                            <a href="${v.video_url}" target="_blank"
                               class="video-url">${v.video_url}</a>
                            <div class="video-date">${date}</div>
                        </div>
                        <span class="video-status ${v.status}">
                            ${statusLabels[v.status] || v.status}
                        </span>
                    </div>
                `;
            });

            if (videos.length < REQUIRED) {
                html += `
                    <button class="action-btn primary" onclick="openBot()"
                            style="margin-top:16px">
                        📤 Отправить ещё видео
                    </button>
                `;
            }

            container.innerHTML = html;
        }

        function renderKey() {
            const container = document.getElementById('keyContent');

            if (userData?.key) {
                container.innerHTML = `
                    <div class="key-display">
                        <div class="key-icon">🔑</div>
                        <div style="font-size:14px;font-weight:600;margin-bottom:8px;
                                    color:var(--text-secondary);position:relative;z-index:1">
                            Твой уникальный ключ
                        </div>
                        <div class="key-value" onclick="copyKey()">${userData.key}</div>
                        <div style="font-size:11px;color:var(--text-muted);
                                    margin-top:8px;position:relative;z-index:1">
                            Нажми на ключ чтобы скопировать
                        </div>
                    </div>

                    <div class="download-section">
                        <div class="download-icon">📥</div>
                        <div class="download-title">Скачать чит</div>
                        <div class="download-desc">
                            Скачай файл и введи ключ для активации
                        </div>
                        <button class="action-btn success" onclick="openLink('${DOWNLOAD}')">
                            📥 Скачать
                        </button>
                    </div>

                    <button class="action-btn outline" onclick="openLink('${CHANNEL}')">
                        📌 Канал с инструкцией
                    </button>

                    <div class="warning-box">
                        <span class="warn-icon">⚠️</span>
                        <span>Ключ одноразовый — никому не передавай!</span>
                    </div>
                `;
            } else if (userData?.is_completed) {
                container.innerHTML = `
                    <div class="card">
                        <div class="card-title">⏳ Ожидание проверки</div>
                        <div class="card-text">
                            Все видео отправлены! Администратор проверит
                            и выдаст ключ. Обычно это занимает до 24 часов.
                        </div>
                    </div>
                `;
            } else {
                const left = REQUIRED - (userData?.video_count || 0);
                container.innerHTML = `
                    <div class="card">
                        <div class="card-title">🔒 Ключ пока недоступен</div>
                        <div class="card-text">
                            Осталось отправить <b>${left}</b> видео.
                            Выполни задание полностью!
                        </div>
                    </div>
                    <button class="action-btn primary" onclick="openBot()">
                        📤 Продолжить задание
                    </button>
                `;
            }
        }

        async function loadLeaderboard() {
            try {
                const res = await fetch(`${API_BASE}/api/leaderboard`);
                const data = await res.json();
                renderLeaderboard(data);
            } catch (e) {
                console.error(e);
            }
        }

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
                const rank = i + 1;
                const medal = medals[i] || `#${rank}`;
                const topClass = i < 3 ? `top-${rank}` : '';
                const isMe = user.user_id == userId;
                const meStyle = isMe ?
                    'border-left: 3px solid var(--cyan);' : '';

                let badge = '';
                if (user.key_issued) {
                    badge = '<span class="leader-badge key">🔑 Ключ</span>';
                } else if (user.is_completed) {
                    badge = '<span class="leader-badge completed">✅ Готов</span>';
                }

                html += `
                    <div class="leader-item ${topClass}"
                         style="${meStyle}">
                        <div class="leader-rank">${medal}</div>
                        <div class="leader-info">
                            <div class="leader-name">
                                ${isMe ? '👈 ' : ''}${user.full_name || 'User'}
                            </div>
                            <div class="leader-username">
                                @${user.username || '—'}
                            </div>
                        </div>
                        <div class="leader-score">
                            ${user.video_count}/${REQUIRED}
                        </div>
                        ${badge}
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        // ===== TABS =====
        function switchTab(tab) {
            // Update nav
            document.querySelectorAll('.nav-tab').forEach(t =>
                t.classList.remove('active'));
            document.getElementById('tab' +
                tab.charAt(0).toUpperCase() + tab.slice(1)
            ).classList.add('active');

            // Update sections
            document.querySelectorAll('.section').forEach(s =>
                s.classList.remove('active'));

            const sectionMap = {
                task: 'sectionTask',
                data: 'sectionData',
                videos: 'sectionVideos',
                key: 'sectionKey',
                top: 'sectionTop'
            };

            document.getElementById(sectionMap[tab]).classList.add('active');

            // Haptic
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.selectionChanged();
            }
        }

        // ===== COPY =====
        function copyText(elementId, blockEl) {
            const el = document.getElementById(elementId);
            let text = el.innerText || el.textContent;

            // For tags, use full text
            if (elementId === 'tagsText') text = FULL_TAGS;
            if (elementId === 'descText') text = FULL_DESC;

            navigator.clipboard.writeText(text).then(() => {
                showToast('✅', 'Скопировано!');

                const btn = blockEl.querySelector('.copy-btn');
                if (btn) {
                    btn.classList.add('copied');
                    btn.textContent = '✅ Готово';
                    setTimeout(() => {
                        btn.classList.remove('copied');
                        btn.textContent = '📋 Копировать';
                    }, 2000);
                }

                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('success');
                }
            }).catch(() => {
                // Fallback
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast('✅', 'Скопировано!');
            });
        }

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

        // ===== TOAST =====
        function showToast(icon, text) {
            const toast = document.getElementById('toast');
            const toastIcon = document.getElementById('toastIcon');
            const toastText = document.getElementById('toastText');

            toastIcon.textContent = icon;
            toastText.textContent = text;
            toast.classList.add('show');

            setTimeout(() => toast.classList.remove('show'), 2500);
        }

        // ===== ACTIONS =====
        function openBot() {
            if (tg) {
                tg.close();
            } else {
                window.open('https://t.me/AimNooBBot', '_blank');
            }
        }

        function openLink(url) {
            if (tg) {
                tg.openLink(url);
            } else {
                window.open(url, '_blank');
            }
        }
    </script>
</body>
</html>
"""


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    await init_db()
    logger.info("Database initialized")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=MINI_APP_HTML)


@app.get("/app", response_class=HTMLResponse)
async def app_page():
    return HTMLResponse(content=MINI_APP_HTML)


# ================== HEALTH ==================
@app.get("/health")
async def health():
    return {"status": "ok", "domain": DOMAIN}


# ================== RUN ==================
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=False
    )
