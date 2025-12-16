"""
Синхронные утилиты для работы с базой telegram_messages.db.
Используются телеграм-ботом для выборки и пометки сообщений.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Sequence

# Файл БД лежит в корне проекта, используем абсолютный путь для надежности
DB_PATH = Path(__file__).resolve().parent.parent / "telegram_messages.db"


def ensure_schema() -> None:
    """Создает таблицу и недостающие колонки (summarized)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                sender TEXT,
                sender_id INTEGER,
                text TEXT,
                date TIMESTAMP,
                summarized INTEGER DEFAULT 0,
                UNIQUE(id, chat_id)
            )
            """
        )

        # Проверяем наличие колонки summarized
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "summarized" not in columns:
            conn.execute("ALTER TABLE messages ADD COLUMN summarized INTEGER DEFAULT 0")
        if "sender_id" not in columns:
            conn.execute("ALTER TABLE messages ADD COLUMN sender_id INTEGER")
        conn.commit()


def fetch_unsummarized(limit: int = 50) -> List[sqlite3.Row]:
    """
    Возвращает последние несуммаризованные сообщения (по дате, новые сверху).
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT id, chat_id, sender, sender_id, text, date
            FROM messages
            WHERE summarized = 0
            ORDER BY date DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cursor.fetchall()


def mark_summarized(message_ids: Sequence[int]) -> None:
    """Помечает сообщения как суммаризованные."""
    if not message_ids:
        return
    with sqlite3.connect(DB_PATH) as conn:
        placeholders = ",".join("?" for _ in message_ids)
        conn.execute(
            f"UPDATE messages SET summarized = 1 WHERE id IN ({placeholders})",
            tuple(message_ids),
        )
        conn.commit()

