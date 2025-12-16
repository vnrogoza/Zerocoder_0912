"""
Телеграм-бот на telebot, отвечающий через GigaChat API.

Запуск:
    1) Создайте .env (можно скопировать env.example) и заполните:
       TELEGRAM_BOT_TOKEN, CLIENT_ID, CLIENT_SECRET
    2) Установите зависимости: pip install -r requirements.txt
    3) Запустите: python -m bot.main_telebot
"""

import logging
import os
import sys
from typing import List, Dict

import telebot
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

from bot.db import ensure_schema, fetch_unsummarized, mark_summarized
from bot.gigachat import (
    generate_summary,
    GigaChatAuthError,
    GigaChatAPIError,
)


load_dotenv()

# Конфигурация логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("telebot_bot")


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не задан. Укажите его в .env")
    raise SystemExit(1)

# Создаем экземпляр бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="Markdown")


@bot.message_handler(commands=["start", "help"])
def handle_start(message: telebot.types.Message) -> None:
    """Приветственное сообщение и подсказка."""
    text = (
        "Привет! Я делаю выжимку сообщений из БД.\n"
        "Команда:\n"
        "/summary — суммаризация последних необработанных сообщений (по умолчанию 50).\n"
        "Сообщения в фоне не обрабатываю — только по команде."
    )
    bot.reply_to(message, text)


def _prepare_prompt(messages: List[Dict[str, str]]) -> str:
    """Формирует текст для отправки в GigaChat."""
    lines = []
    for msg in messages:
        sender = msg.get("sender", "unknown")
        text = msg.get("text", "")
        date = msg.get("date", "")
        lines.append(f"[{date}] {sender}: {text}")
    return "\n".join(lines)


def _send_reply(chat_id: int, text: str, reply_to: int | None = None) -> None:
    """Отправляет длинные ответы частями, чтобы не упасть по ограничению Telegram."""
    if not text:
        bot.send_message(chat_id, "Пустой ответ.", reply_to_message_id=reply_to)
        return

    chunk_size = 3500  # запас от лимита 4096
    for idx in range(0, len(text), chunk_size):
        chunk = text[idx : idx + chunk_size]
        bot.send_message(chat_id, chunk, reply_to_message_id=reply_to if idx == 0 else None)


@bot.message_handler(commands=["summary", "summarize", "summery"])
def handle_summary(message: telebot.types.Message) -> None:
    """Суммаризация последних необработанных сообщений из БД."""
    bot.send_chat_action(message.chat.id, "typing")

    # Парсим лимит из команды: /summary 30
    try:
        parts = message.text.split()
        limit = int(parts[1]) if len(parts) > 1 else 50
        limit = max(1, min(limit, 200))
    except ValueError:
        limit = 50

    try:
        records = fetch_unsummarized(limit)
        if not records:
            bot.reply_to(message, "Нет новых сообщений для выжимки.")
            return

        # Формируем список словарей для prompt
        payload: List[Dict[str, str]] = []
        for row in records:
            payload.append(
                {
                    "sender": row["sender"] or "unknown",
                    "text": row["text"] or "",
                    "date": row["date"] or "",
                }
            )

        prompt = _prepare_prompt(payload)
        logger.info(
            "Суммаризация: найдено %s сообщений (лимит %s), отправитель %s",
            len(records),
            limit,
            message.from_user.id,
        )

        summary = generate_summary(prompt)
        _send_reply(message.chat.id, summary, reply_to=message.id)
        mark_summarized([row["id"] for row in records])
        logger.info(
            "Суммаризовано %s сообщений (лимит %s) пользователем %s",
            len(records),
            limit,
            message.from_user.id,
        )
    except ApiTelegramException as e:
        logger.error("Ошибка Telegram при отправке ответа: %s", e)
        bot.reply_to(message, "Не смог отправить ответ в Telegram (слишком длинный?).")
    except GigaChatAuthError as e:
        logger.error("Ошибка аутентификации GigaChat: %s", e)
        bot.reply_to(
            message,
            "Не удалось получить токен GigaChat. Проверь CLIENT_ID/CLIENT_SECRET.",
        )
    except GigaChatAPIError as e:
        logger.error("Ошибка GigaChat API: %s", e)
        bot.reply_to(message, "GigaChat сейчас недоступен. Попробуй ещё раз позже.")
    except Exception as e:  # noqa: BLE001
        logger.exception("Неожиданная ошибка при суммаризации: %s", e)
        bot.reply_to(message, "Произошла ошибка. Попробуй повторить запрос.")


@bot.message_handler(content_types=["text"])
def handle_text(message: telebot.types.Message) -> None:
    """Любые тексты не обрабатываем — подсказываем использовать /summary."""
    bot.reply_to(
        message,
        "Я не обрабатываю сообщения в фоне. Используй команду /summarize или /summary.",
    )


def main() -> None:
    ensure_schema()
    logger.info("Бот запущен и готов принимать команды суммаризации.")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()

