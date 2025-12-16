"""
Flask-приложение для просмотра статистики и сообщений из базы данных.
"""

from flask import Flask, render_template
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Путь к базе данных (в корне проекта)
DB_PATH = Path(__file__).resolve().parent.parent / "telegram_messages.db"

app = Flask(__name__)


def get_db_stats() -> Dict:
    """
    Получает статистику из базы данных.
    
    Returns:
        dict: Словарь со статистикой
    """
    stats = {
        "total_messages": 0,
        "analyzed_messages": 0,
        "last_summary_date": None
    }
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Всего сообщений
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats["total_messages"] = cursor.fetchone()[0]
            
            # Проанализировано сообщений
            cursor.execute("SELECT COUNT(*) FROM messages WHERE summarized = 1")
            stats["analyzed_messages"] = cursor.fetchone()[0]
            
            # Дата последней выжимки (максимальная дата среди проанализированных)
            cursor.execute(
                "SELECT MAX(date) FROM messages WHERE summarized = 1"
            )
            result = cursor.fetchone()[0]
            if result:
                # Парсим дату из строки
                try:
                    stats["last_summary_date"] = datetime.fromisoformat(result.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # Если формат другой, пробуем просто распарсить
                    try:
                        stats["last_summary_date"] = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        stats["last_summary_date"] = None
            
    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
    
    return stats


def get_all_messages() -> List[Dict]:
    """
    Получает все сообщения из базы данных.
    
    Returns:
        list: Список словарей с сообщениями
    """
    messages = []
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, chat_id, sender, sender_id, text, date, summarized
                FROM messages
                ORDER BY date DESC
                """
            )
            
            for row in cursor.fetchall():
                # Парсим дату
                date_str = row["date"]
                date_obj = None
                if date_str:
                    try:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            date_obj = None
                
                messages.append({
                    "id": row["id"],
                    "chat_id": row["chat_id"],
                    "sender": row["sender"] or "Неизвестно",
                    "sender_id": row["sender_id"],
                    "text": row["text"] or "[без текста]",
                    "date": date_obj,
                    "date_str": date_str,
                    "summarized": bool(row["summarized"])
                })
    
    except Exception as e:
        print(f"Ошибка при получении сообщений: {e}")
    
    return messages


@app.route('/')
def index():
    """Главная страница со статистикой."""
    stats = get_db_stats()
    return render_template('index.html', stats=stats)


@app.route('/messages')
def messages():
    """Страница со списком всех сообщений."""
    messages_list = get_all_messages()
    return render_template('messages.html', messages=messages_list)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

