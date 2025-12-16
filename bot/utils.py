"""
Вспомогательные функции для работы с файлами и текстом.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def read_file(file_path: str) -> str:
    """
    Читает содержимое текстового файла.
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        str: Содержимое файла
    
    Raises:
        FileNotFoundError: Если файл не найден
        IOError: При ошибке чтения файла
    """
    try:
        logger.info(f"Чтение файла: {file_path}")
        
        # Проверяем существование файла
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        # Читаем файл с кодировкой UTF-8
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            logger.warning("Файл пуст или содержит только пробелы")
        
        logger.info(f"Файл успешно прочитан ({len(content)} символов)")
        return content
        
    except FileNotFoundError:
        raise
    except UnicodeDecodeError as e:
        error_msg = f"Ошибка декодирования файла (возможно, не UTF-8): {e}"
        logger.error(error_msg)
        raise IOError(error_msg)
    except Exception as e:
        error_msg = f"Ошибка при чтении файла: {e}"
        logger.error(error_msg)
        raise IOError(error_msg)


def validate_text(text: Optional[str]) -> bool:
    """
    Проверяет, что текст не пустой.
    
    Args:
        text: Текст для проверки
    
    Returns:
        bool: True если текст валиден, False иначе
    """
    if not text:
        return False
    return bool(text.strip())

