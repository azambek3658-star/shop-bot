import aiosqlite
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, path: str = "shop.db"):
        self.path = path
        self.db = None

    async def init(self):
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self.db:
            await self.db.close()

    async def _create_tables(self):
        await self.db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            tg_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            banned INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            age_request TEXT,
            payment_method TEXT,
            status TEXT DEFAULT 'pending',
            payment_link TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            admin_reply TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT OR IGNORE INTO settings VALUES ('shop_open','1');
        INSERT OR IGNORE INTO settings VALUES ('welcome_text','👋 Добро пожаловать!');
        """)
        await self.db.commit()

    async def get_or_create_user(self, tg_id, username=None, full_name=None):
        row = await self.fetchone("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        if not row:
            await self.db.execute("INSERT INTO users(tg_id,username,full_name) VALUES(?,?,?)", (tg_id, username, full_name))
            await self.db.commit()
            row = await self.fetchone("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        return dict(row)

    async def get_user(self, tg_id):
        row = await self.fetchone("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        return dict(row) if row else None

    async def ban_user(self, tg_id, banned=True):
        await self.db.execute("UPDATE users SET banned=? WHERE tg_id=?", (int(banned), tg_id))
        await self.db.commit()

    async def get_all_users(self):
        rows = await self.fetchall("SELECT * FROM users")
        return [dict(r) for r in rows]

    async def get_user_count(self):
        row = await self.fetchone("SELECT COUNT(*) as c FROM users")
        return row["c"]

    async def create_order(self, user_id, category, age_request, payment_method):
        cur = await self.db.execute(
            "INSERT INTO orders(user_id,category,age_request,payment_method) VALUES(?,?,?,?)",
            (user_id, category, age_request, payment_method)
        )
        await self.db.commit()
        return cur.lastrowid

    async def get_order(self, order_id):
        row = await self.fetchone("SELECT * FROM orders WHERE id=?", (order_id,))
        return dict(row) if row else None

    async def update_order(self, order_id, **kwargs):
        sets = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [order_id]
        await self.db.execute(f"UPDATE orders SET {sets} WHERE id=?", values)
        await self.db.commit()

    async def get_user_orders(self, user_id, limit=10):
        rows = await self.fetchall(
            "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(r) for r in rows]

    async def get_orders_today(self):
        row = await self.fetchone("SELECT COUNT(*) as c FROM orders WHERE date(created_at)=date('now') AND status='completed'")
        return row["c"]

    async def create_ticket(self, user_id, message):
        cur = await self.db.execute("INSERT INTO support_tickets(user_id,message) VALUES(?,?)", (user_id, message))
        await self.db.commit()
        return cur.lastrowid

    async def get_open_tickets(self):
        rows = await self.fetchall("SELECT t.*, u.username FROM support_tickets t JOIN users u ON t.user_id=u.tg_id WHERE t.status='open'")
        return [dict(r) for r in rows]

    async def close_ticket(self, ticket_id, reply=None):
        await self.db.execute("UPDATE support_tickets SET status='closed', admin_reply=? WHERE id=?", (reply, ticket_id))
        await self.db.commit()

    async def get_setting(self, key, default=""):
        row = await self.fetchone("SELECT value FROM settings WHERE key=?", (key,))
        return row["value"] if row else default

    async def set_setting(self, key, value):
        await self.db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
        await self.db.commit()

    async def fetchone(self, query, params=()):
        async with self.db.execute(query, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, query, params=()):
        async with self.db.execute(query, params) as cur:
            return await cur.fetchall()
