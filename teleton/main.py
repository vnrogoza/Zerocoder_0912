"""
Основной модуль Telegram-бота на базе Telethon.
Обеспечивает подключение к Telegram, получение сообщений и их сохранение в БД.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
from telethon import TelegramClient, events
from telethon.tl.types import User, Channel, Chat
from telethon.errors import SessionPasswordNeededError, FloodWaitError

from teleton.config import API_ID, API_HASH, SESSION_NAME
from teleton.db import init_db, save_message, get_message_count

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Игнорируемые отправители (не сохраняем их сообщения)
IGNORED_SENDERS = {"ZeroBot0912", "BotFather"}

# Глобальный клиент Telethon
client: Optional[TelegramClient] = None


async def connect_client() -> TelegramClient:
    """
    Подключение к Telegram через Telethon.
    
    Returns:
        TelegramClient: Подключенный клиент
    
    Raises:
        Exception: При ошибке подключения
    """
    global client
    
    try:
        logger.info("Инициализация клиента Telethon...")
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        await client.start()
        
        # Проверка авторизации
        if not await client.is_user_authorized():
            logger.error("Клиент не авторизован. Запустите скрипт для ввода кода авторизации.")
            raise Exception("Клиент не авторизован")
        
        logger.info("Успешное подключение к Telegram")
        me = await client.get_me()
        logger.info(f"Подключен как: {me.first_name} (@{me.username})")
        
        return client
        
    except SessionPasswordNeededError:
        logger.error("Требуется двухфакторная аутентификация (2FA)")
        password = input("Введите пароль 2FA: ")
        await client.sign_in(password=password)
        logger.info("Успешная авторизация с 2FA")
        return client
        
    except Exception as e:
        logger.error(f"Ошибка при подключении: {e}")
        raise


async def get_dialogs(limit: int = 20) -> List:
    """
    Получение списка доступных диалогов (чатов).
    
    Args:
        limit: Максимальное количество диалогов для получения
    
    Returns:
        Список диалогов
    """
    try:
        logger.info(f"Получение списка диалогов (лимит: {limit})...")
        dialogs = await client.get_dialogs(limit=limit)
        
        logger.info(f"Найдено {len(dialogs)} диалогов:")
        for i, dialog in enumerate(dialogs, 1):
            chat_title = dialog.name
            chat_id = dialog.id
            unread_count = dialog.unread_count
            logger.info(f"  {i}. {chat_title} (ID: {chat_id}, непрочитанных: {unread_count})")
        
        return dialogs
        
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {e}")
        return []


async def get_chat_title(chat_id: int) -> str:
    """
    Получение названия чата по его ID.
    
    Args:
        chat_id: ID чата
    
    Returns:
        Название чата
    """
    try:
        entity = await client.get_entity(chat_id)
        if isinstance(entity, (Channel, Chat)):
            return entity.title
        elif isinstance(entity, User):
            return f"{entity.first_name} {entity.last_name or ''}".strip()
        return str(chat_id)
    except Exception as e:
        logger.warning(f"Не удалось получить название чата {chat_id}: {e}")
        return str(chat_id)


async def collect_messages(chat_id: int, limit: int = 100) -> int:
    """
    Сбор последних N сообщений из выбранного чата.
    
    Args:
        chat_id: ID чата
        limit: Количество сообщений для сбора
    
    Returns:
        Количество собранных сообщений
    """
    try:
        logger.info(f"Сбор последних {limit} сообщений из чата {chat_id}...")
        
        chat_title = await get_chat_title(chat_id)
        logger.info(f"Чат: {chat_title}")
        
        collected_count = 0
        
        async for message in client.iter_messages(chat_id, limit=limit):
            try:
                # Получение информации об отправителе
                sender_name = None
                if message.sender:
                    if isinstance(message.sender, User):
                        sender_name = f"{message.sender.first_name} {message.sender.last_name or ''}".strip()
                    else:
                        sender_name = getattr(message.sender, 'title', None) or str(message.sender_id)
                
                # Если отправитель не определен (часто для каналов и групп),
                # используем название чата/канала
                if not sender_name:
                    sender_name = chat_title

                # Пропускаем нежелательных отправителей
                if sender_name in IGNORED_SENDERS:
                    logger.debug("Пропущено сообщение от %s", sender_name)
                    continue
                
                # Получение текста сообщения
                text = message.message or "[медиа или без текста]"
                
                # Определяем sender_id: если отсутствует, используем chat_id (для каналов)
                sender_id_value = message.sender_id if message.sender_id is not None else chat_id
                
                # Конвертируем UTC время в локальное
                if message.date.tzinfo is None:
                    # Если tzinfo отсутствует, считаем время UTC и конвертируем в локальное
                    local_date = message.date.replace(tzinfo=timezone.utc).astimezone()
                else:
                    # Если tzinfo есть, просто конвертируем в локальное
                    local_date = message.date.astimezone()
                
                # Сохранение в базу данных
                saved = await save_message(
                    message_id=message.id,
                    chat_id=chat_id,
                    sender=sender_name,
                    sender_id=sender_id_value,
                    text=text,
                    date=local_date
                )
                
                if saved:
                    collected_count += 1
                    logger.debug(f"Собрано сообщение {message.id}: {text[:50]}...")
                
                # Небольшая задержка для избежания rate limit
                await asyncio.sleep(0.1)
                
            except FloodWaitError as e:
                logger.warning(f"Rate limit! Ожидание {e.seconds} секунд...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения {message.id}: {e}")
                continue
        
        logger.info(f"Собрано {collected_count} новых сообщений из чата {chat_title}")
        return collected_count
        
    except Exception as e:
        logger.error(f"Ошибка при сборе сообщений из чата {chat_id}: {e}")
        return 0


def register_event_handlers():
    """
    Регистрация обработчиков событий Telethon.
    Должна вызываться после создания клиента.
    """
    @client.on(events.NewMessage)
    async def handle_new_message(event):
        """
        Асинхронный обработчик новых сообщений в реальном времени.
        Сохраняет сообщения в базу данных и выводит лог в консоль.
        """
        try:
            message = event.message
            chat = await event.get_chat()
            
            # Получение названия чата
            if isinstance(chat, (Channel, Chat)):
                chat_title = chat.title
            elif isinstance(chat, User):
                chat_title = f"{chat.first_name} {chat.last_name or ''}".strip()
            else:
                chat_title = str(chat.id)
            
            # Получение информации об отправителе
            sender_name = None
            if message.sender:
                if isinstance(message.sender, User):
                    sender_name = f"{message.sender.first_name} {message.sender.last_name or ''}".strip()
                else:
                    sender_name = getattr(message.sender, 'title', None) or str(message.sender_id)
            
            # Если отправитель не определен (часто для каналов и групп),
            # используем название чата/канала
            if not sender_name:
                sender_name = chat_title

            # Пропускаем нежелательных отправителей
            if sender_name in IGNORED_SENDERS:
                logger.debug("Пропущено сообщение от %s", sender_name)
                return
            
            # Получение текста сообщения
            text = message.message or "[медиа или без текста]"
            
            # Определяем sender_id: если отсутствует, используем chat.id (для каналов)
            sender_id_value = message.sender_id if message.sender_id is not None else chat.id
            
            # Конвертируем UTC время в локальное
            if message.date.tzinfo is None:
                # Если tzinfo отсутствует, считаем время UTC и конвертируем в локальное
                local_date = message.date.replace(tzinfo=timezone.utc).astimezone()
            else:
                # Если tzinfo есть, просто конвертируем в локальное
                local_date = message.date.astimezone()
            
            # Сохранение в базу данных
            await save_message(
                message_id=message.id,
                chat_id=chat.id,
                sender=sender_name,
                sender_id=sender_id_value,
                text=text,
                date=local_date
            )
            
            # Вывод короткого лога в консоль
            print(f"[{chat_title}] {sender_name}: {text[:100]}")
            logger.info(f"Новое сообщение из [{chat_title}] от {sender_name}: {text[:100]}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке нового сообщения: {e}")


async def start_live_listener():
    """
    Запуск live-слушателя новых сообщений.
    """
    logger.info("Запуск live-слушателя новых сообщений...")
    logger.info("Ожидание новых сообщений... (Ctrl+C для остановки)")
    
    # Клиент уже подключен, обработчик событий уже зарегистрирован
    # Просто держим соединение активным
    await client.run_until_disconnected()


async def main():
    """
    Основная функция с примером использования.
    """
    try:
        # Инициализация базы данных
        await init_db()
        logger.info("База данных готова")
        
        # Подключение к Telegram
        await connect_client()
        
        # Регистрация обработчиков событий
        register_event_handlers()
        
        # Получение списка чатов
        dialogs = await get_dialogs(limit=20)
        
        if not dialogs:
            logger.warning("Не найдено диалогов")
            return
        
        # Пример: сбор последних 100 сообщений из первого чата
        if dialogs:
            first_chat_id = dialogs[0].id
            first_chat_title = dialogs[0].name
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Пример: сбор сообщений из чата '{first_chat_title}'")
            logger.info(f"{'='*50}\n")
            
            await collect_messages(first_chat_id, limit=100)
            
            # Показать статистику
            total_messages = await get_message_count()
            chat_messages = await get_message_count(first_chat_id)
            logger.info(f"\nСтатистика БД:")
            logger.info(f"  Всего сообщений: {total_messages}")
            logger.info(f"  Сообщений из '{first_chat_title}': {chat_messages}")
        
        # Запуск live-слушателя новых сообщений
        logger.info(f"\n{'='*50}")
        logger.info("Запуск live-слушателя...")
        logger.info(f"{'='*50}\n")
        
        await start_live_listener()
        
    except KeyboardInterrupt:
        logger.info("\nОстановка бота по запросу пользователя...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if client:
            await client.disconnect()
            logger.info("Клиент отключен")


if __name__ == '__main__':
    # Запуск асинхронной функции
    asyncio.run(main())

