"""ذخیره سفارش‌ها، مشتریان، پروژه‌ها و اخطارهای گروه در SQLite."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from config import DATABASE_FILE

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    username TEXT,
    full_name TEXT,
    category TEXT NOT NULL,
    service TEXT NOT NULL,
    description TEXT NOT NULL,
    phone TEXT NOT NULL,
    telegram_handle TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    details TEXT NOT NULL,
    client_name TEXT,
    client_phone TEXT,
    client_telegram TEXT,
    source TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS warnings (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    last_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
"""


@contextmanager
def connect():
    Path(DATABASE_FILE).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def upsert_user(telegram_id: int, username: str | None, full_name: str, phone: str | None = None) -> None:
    with connect() as conn:
        existing = conn.execute(
            "SELECT phone FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        now = datetime.now().isoformat(timespec="seconds")
        if existing:
            conn.execute(
                """
                UPDATE users
                SET username = ?, full_name = ?, phone = COALESCE(?, phone)
                WHERE telegram_id = ?
                """,
                (username, full_name, phone, telegram_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO users (telegram_id, username, full_name, phone, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (telegram_id, username, full_name, phone, now),
            )


def add_order(
    telegram_id: int,
    username: str | None,
    full_name: str,
    category: str,
    service: str,
    description: str,
    phone: str,
    telegram_handle: str,
) -> int:
    upsert_user(telegram_id, username, full_name, phone)
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO orders (
                telegram_id, username, full_name, category, service,
                description, phone, telegram_handle, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
            """,
            (
                telegram_id,
                username,
                full_name,
                category,
                service,
                description,
                phone,
                telegram_handle,
                now,
            ),
        )
        return int(cur.lastrowid)


def list_orders(status: str | None = None, limit: int = 20) -> list[sqlite3.Row]:
    with connect() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def set_order_status(order_id: int, status: str) -> bool:
    with connect() as conn:
        cur = conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
        )
        return cur.rowcount > 0


def list_users(limit: int = 30) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()


def add_project(
    title: str,
    details: str,
    client_name: str = "",
    client_phone: str = "",
    client_telegram: str = "",
    source: str = "",
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO projects (
                title, details, client_name, client_phone, client_telegram, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, details, client_name, client_phone, client_telegram, source, now),
        )
        return int(cur.lastrowid)


def list_projects(limit: int = 20) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM projects ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def add_warning(chat_id: int, user_id: int) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        row = conn.execute(
            "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        ).fetchone()
        if row:
            count = int(row["count"]) + 1
            conn.execute(
                "UPDATE warnings SET count = ?, last_at = ? WHERE chat_id = ? AND user_id = ?",
                (count, now, chat_id, user_id),
            )
            return count
        conn.execute(
            "INSERT INTO warnings (chat_id, user_id, count, last_at) VALUES (?, ?, 1, ?)",
            (chat_id, user_id, now),
        )
        return 1


def list_warning_stats(limit: int = 20) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT chat_id, user_id, count, last_at
            FROM warnings
            WHERE count > 0
            ORDER BY count DESC, last_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
