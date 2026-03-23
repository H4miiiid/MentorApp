from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from .config import settings


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL DEFAULT '',
                student_id_number TEXT NOT NULL DEFAULT '',
                full_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('student', 'professor')),
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_user_columns(conn)
        _ensure_user_indexes(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professor_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (professor_id) REFERENCES users (id),
                FOREIGN KEY (student_id) REFERENCES users (id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                student_code TEXT NOT NULL,
                corrected_code TEXT NOT NULL,
                mistakes_diff TEXT NOT NULL,
                grade_percent REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (student_id) REFERENCES users (id)
            )
            """
        )


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


def _ensure_user_columns(conn: sqlite3.Connection) -> None:
    columns = _column_names(conn, "users")
    if "email" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    if "student_id_number" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN student_id_number TEXT NOT NULL DEFAULT ''")


def _ensure_user_indexes(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
        ON users(email)
        WHERE email <> ''
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_student_id_unique
        ON users(student_id_number)
        WHERE student_id_number <> ''
        """
    )


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
    return dict(row) if row is not None else None


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def execute_insert(query: str, params: tuple[Any, ...]) -> int:
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return int(cur.lastrowid)


def utc_now_iso() -> str:
    return _utc_now_iso()
