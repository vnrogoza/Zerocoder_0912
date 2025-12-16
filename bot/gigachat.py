"""
Модуль для работы с GigaChat API.
Обеспечивает получение токена доступа и генерацию выжимок текста.
"""

import requests
import logging
from typing import Optional
from dotenv import load_dotenv
import os
import urllib3
import uuid
from datetime import datetime

# Отключаем предупреждения о небезопасных SSL сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Загружаем переменные окружения из .env
load_dotenv()

logger = logging.getLogger(__name__)
# Добавляем файловый логгер для трассировки запросов/ответов GigaChat
if not logger.handlers:
    log_file = os.path.join(os.path.dirname(__file__), "gigachat.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

# URL эндпоинтов GigaChat API
OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_COMPLETIONS_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Получаем credentials из переменных окружения
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


class GigaChatError(Exception):
    """Базовое исключение для ошибок GigaChat API"""
    pass


class GigaChatAuthError(GigaChatError):
    """Ошибка аутентификации в GigaChat API"""
    pass


class GigaChatAPIError(GigaChatError):
    """Ошибка при запросе к GigaChat API"""
    pass


def get_access_token() -> str:
    """
    Получает OAuth токен доступа для работы с GigaChat API.
    Использует Basic авторизацию через заголовок Authorization.
    
    Returns:
        str: Access token для использования в API запросах
    
    Raises:
        GigaChatAuthError: При ошибке аутентификации
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise GigaChatAuthError(
            "CLIENT_ID и CLIENT_SECRET должны быть установлены в .env файле"
        )
    
    try:
        logger.info("Получение access token от GigaChat API...")
        
        # Используем CLIENT_SECRET напрямую из .env
        credentials = CLIENT_SECRET
        
        # Генерируем RqUID (можно использовать CLIENT_ID или UUID)
        rquid = CLIENT_ID
        
        # Формируем заголовки запроса согласно test.py
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": rquid,
            "Authorization": 'Basic '+credentials
        }
        
        # Тело запроса для получения токена (только scope)
        payload = {
            "scope": "GIGACHAT_API_PERS"
        }
        
        # Отправляем POST запрос
        # verify=False отключает проверку SSL сертификата (для обхода проблем с сертификатами)
        logger.info(
            "GigaChat request: method=POST url=%s payload=%s headers=%s",
            OAUTH_URL,
            payload,
            {k: ("***" if k.lower() == "authorization" else v) for k, v in headers.items()},
        )
        response = requests.post(
            OAUTH_URL,
            headers=headers,
            data=payload,
            verify=False,
            timeout=30
        )
        
        # Проверяем статус ответа
        if response.status_code != 200:
            error_msg = f"Ошибка аутентификации: {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            
            logger.error(error_msg)
            raise GigaChatAuthError(error_msg)
        
        # Логируем ответ (без токена)
        try:
            resp_json = response.json()
        except Exception:
            resp_json = response.text
        logger.info(
            "GigaChat response: status=%s body=%s",
            response.status_code,
            resp_json,
        )

        # Парсим ответ и извлекаем токен
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            error_msg = "Токен доступа не найден в ответе API"
            logger.error(error_msg)
            raise GigaChatAuthError(error_msg)
        
        logger.info("Access token успешно получен")
        return access_token
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка сети при получении токена: {e}"
        logger.error(error_msg)
        raise GigaChatAuthError(error_msg)
    except Exception as e:
        error_msg = f"Неожиданная ошибка при получении токена: {e}"
        logger.error(error_msg)
        raise GigaChatAuthError(error_msg)


def _call_chat_api(messages: list[dict], model: str = "GigaChat") -> str:
    """
    Делает вызов chat/completions и возвращает текст ответа.
    Используется как для summary, так и для произвольных чат-запросов.
    """
    if not messages:
        raise ValueError("Список сообщений пуст")

    try:
        access_token = get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages
        }

        logger.info(
            "GigaChat request: method=POST url=%s payload=%s headers=%s",
            CHAT_COMPLETIONS_URL,
            payload,
            {"Content-Type": headers["Content-Type"], "Accept": headers["Accept"], "Authorization": "***"},
        )

        response = requests.post(
            CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=30,
            verify=False
        )

        if response.status_code != 200:
            error_msg = f"Ошибка API: {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f" - {error_detail}"
            except Exception:
                error_msg += f" - {response.text}"

            logger.error(error_msg)
            raise GigaChatAPIError(error_msg)

        try:
            response_data = response.json()
        except Exception:
            response_data = {}

        logger.info(
            "GigaChat response: status=%s body=%s",
            response.status_code,
            response_data if response_data else response.text,
        )

        if "choices" not in response_data or not response_data["choices"]:
            error_msg = "Неожиданный формат ответа API: отсутствует поле choices"
            logger.error(error_msg)
            raise GigaChatAPIError(error_msg)

        choice = response_data["choices"][0]
        if "message" not in choice or "content" not in choice["message"]:
            error_msg = "Неожиданный формат ответа API: отсутствует поле message.content"
            logger.error(error_msg)
            raise GigaChatAPIError(error_msg)

        return choice["message"]["content"]

    except GigaChatAuthError:
        raise
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка сети при запросе к API: {e}"
        logger.error(error_msg)
        raise GigaChatAPIError(error_msg)
    except GigaChatAPIError:
        raise
    except Exception as e:
        error_msg = f"Неожиданная ошибка при обращении к chat/completions: {e}"
        logger.error(error_msg)
        raise GigaChatAPIError(error_msg)


def chat_completion(messages: list[dict], model: str = "GigaChat") -> str:
    """
    Универсальный вызов GigaChat chat/completions.

    Args:
        messages: список сообщений в формате OpenAI (role/content)
        model: имя модели (по умолчанию GigaChat)
    """
    logger.info("Запрос к GigaChat chat/completions")
    return _call_chat_api(messages=messages, model=model)


def generate_summary(text: str) -> str:
    """
    Генерирует краткую выжимку (summary) текста через GigaChat API.
    
    Args:
        text: Текст для обработки
    
    Returns:
        str: Краткая выжимка текста
    
    Raises:
        GigaChatAPIError: При ошибке запроса к API
        GigaChatAuthError: При ошибке аутентификации
    """
    if not text or not text.strip():
        raise ValueError("Текст не может быть пустым")

    logger.info("Генерация выжимки текста через GigaChat API...")

    messages = [
        {
            "role": "system",
            "content": "Ты – ассистент, который делает краткие выжимки текста."
        },
        {
            "role": "user",
            "content": text
        }
    ]

    return _call_chat_api(messages=messages)

