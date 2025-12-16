"""
Модуль для работы с базой данных SQLite.
Обеспечивает сохранение сообщений из Telegram.
"""

import aiosqlite
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Путь к файлу базы данных
DB_PATH = "telegram_messages.db"


async def _ensure_schema(db: aiosqlite.Connection) -> None:
    """Добавляет недостающие колонки без потери данных."""
    cursor = await db.execute("PRAGMA table_info(messages)")
    columns = await cursor.fetchall()
    column_names = {row[1] for row in columns}

    # Колонка для отметки суммаризации
    if "summarized" not in column_names:
        await db.execute("ALTER TABLE messages ADD COLUMN summarized INTEGER DEFAULT 0")
        logger.info("Добавлена колонка summarized в таблицу messages")

    # Колонка идентификатора отправителя
    if "sender_id" not in column_names:
        await db.execute("ALTER TABLE messages ADD COLUMN sender_id INTEGER")
        logger.info("Добавлена колонка sender_id в таблицу messages")

    await db.commit()


async def init_db():
    """
    Инициализация базы данных.
    Создает таблицу messages, если она не существует.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
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
            await _ensure_schema(db)
            await db.commit()
            logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise


async def save_message(
    message_id: int,
    chat_id: int,
    sender: Optional[str],
    sender_id: Optional[int],
    text: Optional[str],
    date: datetime,
) -> bool:
    """
    Сохранение сообщения в базу данных.
    
    Args:
        message_id: ID сообщения в Telegram
        chat_id: ID чата
        sender: Имя отправителя
        text: Текст сообщения
        date: Дата и время сообщения
    
    Returns:
        True если сообщение сохранено, False если уже существует (дубль)
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Попытка вставить сообщение
            # Если сообщение уже существует (дубль), SQLite вернет ошибку
            # Используем INSERT OR IGNORE для пропуска дублей
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO messages
                    (id, chat_id, sender, sender_id, text, date, summarized)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (message_id, chat_id, sender, sender_id, text, date),
            )
            
            await db.commit()
            
            # Если была вставлена новая строка, affected_rows будет > 0
            if cursor.rowcount > 0:
                logger.debug(f"Сообщение {message_id} из чата {chat_id} сохранено в БД")
                return True
            else:
                logger.debug(f"Сообщение {message_id} из чата {chat_id} уже существует (дубль)")
                return False
                
    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения в БД: {e}")
        return False


async def get_message_count(chat_id: Optional[int] = None) -> int:
    """
    Получить количество сообщений в базе данных.
    
    Args:
        chat_id: Опциональный ID чата для фильтрации
    
    Returns:
        Количество сообщений
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if chat_id:
                cursor = await db.execute(
                    'SELECT COUNT(*) FROM messages WHERE chat_id = ?',
                    (chat_id,)
                )
            else:
                cursor = await db.execute('SELECT COUNT(*) FROM messages')
            
            result = await cursor.fetchone()
            return result[0] if result else 0
            
    except Exception as e:
        logger.error(f"Ошибка при получении количества сообщений: {e}")
        return 0

