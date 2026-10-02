"""Database layer — SQLite via aiosqlite."""

from __future__ import annotations

import aiosqlite


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, path: str = "bot.db"):
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._create_tables()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def _create_tables(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TEXT DEFAULT (datetime('now')),
                captcha_passed INTEGER DEFAULT 0,
                warn_count INTEGER DEFAULT 0,
                is_muted INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                admin_id INTEGER,
                reason TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS chat_user_state (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                warn_count INTEGER DEFAULT 0,
                is_muted INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS faq_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                keywords TEXT NOT NULL,
                response TEXT NOT NULL,
                created_by INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome_message TEXT DEFAULT 'Welcome! Please read the rules.',
                rules_text TEXT DEFAULT 'Be respectful. No spam. No scam links.',
                captcha_enabled INTEGER DEFAULT 1,
                antispam_enabled INTEGER DEFAULT 1,
                raid_protection INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                sentiment_score REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)

    # --- User methods ---

    async def get_or_create_user(self, user_id: int, username: str | None = None) -> dict:
        await self._db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        await self._db.commit()
        async with self._db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(zip([d[0] for d in cursor.description], row))


    async def set_captcha_passed(self, user_id: int) -> None:
        await self._db.execute(
            "UPDATE users SET captcha_passed = 1 WHERE user_id = ?", (user_id,)
        )
        await self._db.commit()

    async def add_warn(self, user_id: int, admin_id: int, reason: str, chat_id: int) -> int:
        await self.get_or_create_user(user_id)
        await self._db.execute(
            "INSERT INTO warns (user_id, admin_id, reason) VALUES (?, ?, ?)",
            (user_id, admin_id, reason),
        )
        await self._db.execute(
            """INSERT INTO chat_user_state (chat_id, user_id, warn_count) VALUES (?, ?, 1)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET warn_count = warn_count + 1""",
            (chat_id, user_id),
        )
        await self._db.commit()
        async with self._db.execute(
            "SELECT warn_count FROM chat_user_state WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 1

    async def set_muted(self, user_id: int, muted: bool, chat_id: int) -> None:
        await self._db.execute(
            """INSERT INTO chat_user_state (chat_id, user_id, is_muted) VALUES (?, ?, ?)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET is_muted = excluded.is_muted""",
            (chat_id, user_id, int(muted))
        )
        await self._db.commit()

    async def set_banned(self, user_id: int, banned: bool, chat_id: int) -> None:
        await self._db.execute(
            """INSERT INTO chat_user_state (chat_id, user_id, is_banned) VALUES (?, ?, ?)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET is_banned = excluded.is_banned""",
            (chat_id, user_id, int(banned))
        )
        await self._db.commit()

    # --- FAQ methods ---

    async def add_faq(self, chat_id: int, keywords: str, response: str, created_by: int) -> int:
        cursor = await self._db.execute(
            "INSERT INTO faq_entries (chat_id, keywords, response, created_by) VALUES (?, ?, ?, ?)",
            (chat_id, keywords, response, created_by),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_faqs(self, chat_id: int) -> list[dict]:
        async with self._db.execute(
            "SELECT id, keywords, response FROM faq_entries WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "keywords": r[1], "response": r[2]} for r in rows]

    async def delete_faq(self, faq_id: int, chat_id: int) -> None:
        await self._db.execute("DELETE FROM faq_entries WHERE id = ? AND chat_id = ?", (faq_id, chat_id))
        await self._db.commit()

    # --- Chat settings ---

    async def get_settings(self, chat_id: int) -> dict:
        await self._db.execute(
            "INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,)
        )
        await self._db.commit()
        async with self._db.execute(
            "SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(zip([d[0] for d in cursor.description], row))

    # --- Message log (for sentiment) ---

    async def log_message(self, chat_id: int, user_id: int, sentiment: float) -> None:
        await self._db.execute(
            "INSERT INTO message_log (chat_id, user_id, sentiment_score) VALUES (?, ?, ?)",
            (chat_id, user_id, sentiment),
        )
        await self._db.commit()

    async def get_sentiment_avg(self, chat_id: int, hours: int = 24) -> float:
        async with self._db.execute(
            """SELECT AVG(sentiment_score) FROM message_log
               WHERE chat_id = ? AND created_at > datetime('now', ?)""",
            (chat_id, f"-{hours} hours"),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else 0.0
