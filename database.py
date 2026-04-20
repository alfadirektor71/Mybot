import aiosqlite
import logging
from datetime import datetime

import os
DB_PATH = os.path.join("data", "bot_database.db")
logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                referred_by INTEGER DEFAULT NULL,
                today_income INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                last_active INTEGER DEFAULT 0,
                bonus_claimed_date TEXT DEFAULT '',
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                payment_method TEXT DEFAULT 'card',
                wallet_number TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                reward INTEGER NOT NULL,
                link TEXT,
                task_type TEXT DEFAULT 'channel',
                photo_id TEXT DEFAULT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, task_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # channels: type = 'channel_public'|'channel_private'|'channel_request'|'group_public'|'group_private'|'group_request'|'link'
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                channel_name TEXT NOT NULL,
                channel_link TEXT NOT NULL,
                channel_type TEXT DEFAULT 'channel_public',
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                full_name TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        defaults = [
            ("referral_bonus", "180"),
            ("min_withdraw", "5000"),
            ("currency", "som"),
            ("payment_channel", "@foydauzb_tolov"),
            ("bot_active", "1"),
            ("contact_info", "@admin"),
            ("bonus_min", "10"),
            ("bonus_max", "100"),
        ]
        for key, value in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

        # Default to'lov usullari
        default_methods = [
            ("humo", "Humo"),
            ("uzcard", "Uzcard"),
            ("visa", "Visa"),
            ("phone", "Nomerga"),
        ]
        for name, display in default_methods:
            await db.execute(
                "INSERT OR IGNORE INTO payment_methods (name, display_name) VALUES (?, ?)",
                (name, display)
            )

        await db.commit()
        logger.info("DB ishga tushdi.")


# ===================== USER =====================

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as c:
            return await c.fetchone()


async def create_user(user_id: int, username: str, full_name: str, referred_by: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by) VALUES (?,?,?,?)",
            (user_id, username, full_name, referred_by)
        )
        await db.commit()


async def update_last_active(user_id: int):
    import time
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_active=? WHERE user_id=?", (int(time.time()), user_id))
        await db.commit()


async def admin_update_balance(user_id: int, amount: int):
    """Admin tomonidan balans o'zgartirish — foydalanuvchiga xabar bormaydi"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def admin_update_balance(user_id: int, amount: int):
    """Admin balansni o'zgartiradi — foydalanuvchiga xabar bormaydi, total_earned ham o'zgarmaydi"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def update_balance(user_id: int, amount: int, silent: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        if amount > 0:
            await db.execute(
                "UPDATE users SET total_earned=total_earned+?, today_income=today_income+? WHERE user_id=?",
                (amount, amount, user_id)
            )
        await db.commit()


async def get_top10():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY total_earned DESC LIMIT 10") as c:
            return await c.fetchall()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as c:
            return await c.fetchall()


async def execute_referral_count(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET referral_count=referral_count+1 WHERE user_id=?", (user_id,))
        await db.commit()


async def ban_user(user_id: int, ban: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if ban else 0, user_id))
        await db.commit()


async def get_referral_stats(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE referred_by=?", (user_id,)) as c:
            referrals = await c.fetchall()
    active = sum(1 for r in referrals if r["balance"] > 0)
    return len(referrals), active, len(referrals) - active


async def get_stats():
    import time
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total_users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned=0") as c:
            active_users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'") as c:
            pending_payments = (await c.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved'") as c:
            total_paid = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE datetime(joined_at) >= datetime('now','-1 day')") as c:
            day1 = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE datetime(joined_at) >= datetime('now','-30 days')") as c:
            day30 = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE datetime(joined_at) >= datetime('now','-60 days')") as c:
            day60 = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE datetime(joined_at) >= datetime('now','-90 days')") as c:
            day90 = (await c.fetchone())[0]
        now = int(time.time())
        online_threshold = now - 300  # 5 daqiqa ichida
        async with db.execute("SELECT COUNT(*) FROM users WHERE last_active>=?", (online_threshold,)) as c:
            online_now = (await c.fetchone())[0]
    return {
        "total_users": total_users,
        "active_users": active_users,
        "pending_payments": pending_payments,
        "total_paid": total_paid,
        "day1": day1,
        "day30": day30,
        "day60": day60,
        "day90": day90,
        "online_now": online_now,
    }


async def claim_daily_bonus(user_id: int, amount: int) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT bonus_claimed_date FROM users WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
        if row and row[0] == today:
            return False
        await db.execute("UPDATE users SET bonus_claimed_date=? WHERE user_id=?", (today, user_id))
        await db.commit()
    await update_balance(user_id, amount)
    return True


# ===================== TO'LOV =====================

async def create_payment(user_id: int, amount: int, wallet_number: str, payment_method: str = "card"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO payments (user_id, amount, wallet_number, payment_method) VALUES (?,?,?,?)",
            (user_id, amount, wallet_number, payment_method)
        )
        await db.commit()


async def get_pending_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT p.*, u.full_name, u.username FROM payments p JOIN users u ON p.user_id=u.user_id WHERE p.status='pending' ORDER BY p.created_at DESC"
        ) as c:
            return await c.fetchall()


async def update_payment_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, payment_id)
        )
        await db.commit()


async def get_payment_by_id(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)) as c:
            return await c.fetchone()


async def get_payment_methods():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payment_methods WHERE is_active=1") as c:
            return await c.fetchall()


async def add_payment_method(name: str, display_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO payment_methods (name, display_name) VALUES (?,?)", (name, display_name))
        await db.commit()


async def toggle_payment_method(method_id: int, active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payment_methods SET is_active=? WHERE id=?", (1 if active else 0, method_id))
        await db.commit()


async def get_all_payment_methods():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payment_methods") as c:
            return await c.fetchall()


# ===================== VAZIFALAR =====================

async def get_active_tasks():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE is_active=1") as c:
            return await c.fetchall()


async def get_task_by_id(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)) as c:
            return await c.fetchone()


async def add_task(title: str, description: str, reward: int, link: str, task_type: str = "channel", photo_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tasks (title, description, reward, link, task_type, photo_id) VALUES (?,?,?,?,?,?)",
            (title, description, reward, link, task_type, photo_id)
        )
        await db.commit()


async def complete_task(user_id: int, task_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO user_tasks (user_id, task_id) VALUES (?,?)", (user_id, task_id))
            await db.commit()
            return True
        except Exception:
            return False


async def is_task_completed(user_id: int, task_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM user_tasks WHERE user_id=? AND task_id=?", (user_id, task_id)) as c:
            return await c.fetchone() is not None


async def delete_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET is_active=0 WHERE id=?", (task_id,))
        await db.commit()


# ===================== SOZLAMALAR =====================

async def get_setting(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as c:
            row = await c.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()


# ===================== KANALLAR =====================

async def get_active_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels WHERE is_active=1") as c:
            return await c.fetchall()


async def add_channel(channel_id: str, channel_name: str, channel_link: str, channel_type: str = "channel_public"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO channels (channel_id, channel_name, channel_link, channel_type) VALUES (?,?,?,?)",
            (channel_id, channel_name, channel_link, channel_type)
        )
        await db.commit()


async def remove_channel(ch_db_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE channels SET is_active=0 WHERE id=?", (ch_db_id,))
        await db.commit()


async def get_all_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels WHERE is_active=1") as c:
            return await c.fetchall()


# ===================== ADMINLAR =====================

async def get_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins") as c:
            return await c.fetchall()


async def add_admin(user_id: int, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id, full_name) VALUES (?,?)", (user_id, full_name))
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


async def is_admin(user_id: int) -> bool:
    from config import ADMIN_IDS
    if user_id in ADMIN_IDS:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM admins WHERE user_id=?", (user_id,)) as c:
            return await c.fetchone() is not None
