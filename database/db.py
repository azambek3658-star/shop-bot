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
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '📦',
            visible INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            price_stars INTEGER DEFAULT 0,
            visible INTEGER DEFAULT 1,
            supplier_code TEXT
        );
        CREATE TABLE IF NOT EXISTS product_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            data TEXT NOT NULL,
            sold INTEGER DEFAULT 0,
            order_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            total_price REAL NOT NULL,
            currency TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
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

    async def get_categories(self, visible_only=True):
        q = "SELECT * FROM categories"
        if visible_only:
            q += " WHERE visible=1"
        rows = await self.fetchall(q)
        return [dict(r) for r in rows]

    async def create_category(self, name, emoji="📦"):
        cur = await self.db.execute("INSERT INTO categories(name,emoji) VALUES(?,?)", (name, emoji))
        await self.db.commit()
        return cur.lastrowid

    async def delete_category(self, cat_id):
        await self.db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        await self.db.commit()

    async def get_products(self, category_id=None, visible_only=True):
        q = "SELECT * FROM products WHERE 1=1"
        params = []
        if visible_only:
            q += " AND visible=1"
        if category_id:
            q += " AND category_id=?"
            params.append(category_id)
        rows = await self.fetchall(q, params)
        return [dict(r) for r in rows]

    async def get_product(self, product_id):
        row = await self.fetchone("SELECT * FROM products WHERE id=?", (product_id,))
        return dict(row) if row else None

    async def create_product(self, name, description, price, price_stars, category_id, supplier_code=""):
        cur = await self.db.execute(
            "INSERT INTO products(name,description,price,price_stars,category_id,supplier_code) VALUES(?,?,?,?,?,?)",
            (name, description, price, price_stars, category_id, supplier_code)
        )
        await self.db.commit()
        return cur.lastrowid

    async def update_product(self, product_id, **kwargs):
        sets = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [product_id]
        await self.db.execute(f"UPDATE products SET {sets} WHERE id=?", values)
        await self.db.commit()

    async def delete_product(self, product_id):
        await self.db.execute("DELETE FROM products WHERE id=?", (product_id,))
        await self.db.commit()

    async def get_stock_count(self, product_id):
        row = await self.fetchone("SELECT COUNT(*) as c FROM product_items WHERE product_id=? AND sold=0", (product_id,))
        return row["c"]

    async def add_items(self, product_id, items):
        await self.db.executemany("INSERT INTO product_items(product_id,data) VALUES(?,?)", [(product_id, item) for item in items])
        await self.db.commit()

    async def pop_items(self, product_id, count=1):
        rows = await self.fetchall("SELECT id, data FROM product_items WHERE product_id=? AND sold=0 LIMIT ?", (product_id, count))
        ids = [r["id"] for r in rows]
        if ids:
            placeholders = ",".join("?" * len(ids))
            await self.db.execute(f"UPDATE product_items SET sold=1 WHERE id IN ({placeholders})", ids)
            await self.db.commit()
        return [r["data"] for r in rows]

    async def create_order(self, user_id, product_id, quantity, total_price, currency, payment_method):
        cur = await self.db.execute(
            "INSERT INTO orders(user_id,product_id,quantity,total_price,currency,payment_method) VALUES(?,?,?,?,?,?)",
            (user_id, product_id, quantity, total_price, currency, payment_method)
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

    async def complete_order(self, order_id):
        await self.db.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
        await self.db.commit()

    async def get_user_orders(self, user_id, limit=10):
        rows = await self.fetchall(
            "SELECT o.*, p.name as product_name FROM orders o JOIN products p ON o.product_id=p.id WHERE o.user_id=? ORDER BY o.created_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(r) for r in rows]

    async def get_orders_today(self):
        row = await self.fetchone("SELECT COUNT(*) as c FROM orders WHERE date(created_at)=date('now') AND status='completed'")
        return row["c"]

    async def get_revenue_today(self):
        row = await self.fetchone("SELECT COALESCE(SUM(total_price),0) as s FROM orders WHERE date(created_at)=date('now') AND status='completed'")
        return row["s"]

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
