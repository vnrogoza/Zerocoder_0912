"""
CLI-приложение для генерации выжимок текста через GigaChat API.

Использование:
    python -m bot.main summary --file messages.txt
    python -m bot.main summary --text "любые сообщения"
"""

import argparse
import sys
import logging
from pathlib import Path

from bot.gigachat import generate_summary, GigaChatError, GigaChatAuthError, GigaChatAPIError
from bot.utils import read_file, validate_text

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """
    Настраивает парсер аргументов командной строки.
    
    Returns:
        argparse.ArgumentParser: Настроенный парсер
    """
    parser = argparse.ArgumentParser(
        description='CLI-инструмент для генерации выжимок текста через GigaChat API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python -m bot.main summary --file messages.txt
  python -m bot.main summary --text "Ваш текст для обработки"
        """
    )
    
    # Создаем подпарсеры для команд
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда summary
    summary_parser = subparsers.add_parser(
        'summary',
        help='Генерирует краткую выжимку текста'
    )
    
    # Группа для взаимно исключающих аргументов
    input_group = summary_parser.add_mutually_exclusive_group(required=False)
    
    input_group.add_argument(
        '--file',
        type=str,
        help='Путь к файлу с текстом для обработки'
    )
    
    input_group.add_argument(
        '--text',
        type=str,
        help='Текст для обработки (строка)'
    )
    
    return parser


def get_text_from_args(args: argparse.Namespace) -> str:
    """
    Извлекает текст из аргументов командной строки.
    Приоритет: --text > --file
    
    Args:
        args: Аргументы командной строки
    
    Returns:
        str: Текст для обработки
    
    Raises:
        ValueError: Если текст не указан или пуст
    """
    text = None
    
    # Приоритет у --text
    if args.text:
        text = args.text
        logger.info("Используется текст из аргумента --text")
    elif args.file:
        text = read_file(args.file)
        logger.info(f"Используется текст из файла: {args.file}")
    else:
        raise ValueError(
            "Не указан источник текста. Используйте --file или --text.\n"
            "Запустите с --help для справки."
        )
    
    # Проверяем, что текст не пустой
    if not validate_text(text):
        raise ValueError("Текст не может быть пустым")
    
    return text


def main():
    """
    Главная функция CLI-приложения.
    """
    parser = setup_parser()
    args = parser.parse_args()
    
    # Проверяем, что команда указана
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Обрабатываем команду summary
    if args.command == 'summary':
        try:
            # Получаем текст для обработки
            text = get_text_from_args(args)
            
            logger.info(f"Обработка текста ({len(text)} символов)...")
            
            # Генерируем выжимку
            summary = generate_summary(text)
            
            # Выводим результат
            print("\n" + "="*60)
            print("ВЫЖИМКА ТЕКСТА:")
            print("="*60)
            print(summary)
            print("="*60 + "\n")
            
            logger.info("Выжимка успешно сгенерирована и выведена")
            
        except ValueError as e:
            logger.error(f"Ошибка валидации: {e}")
            print(f"\nОшибка: {e}\n", file=sys.stderr)
            sys.exit(1)
            
        except GigaChatAuthError as e:
            logger.error(f"Ошибка аутентификации: {e}")
            print(f"\nОшибка аутентификации: {e}", file=sys.stderr)
            print("Проверьте правильность CLIENT_ID и CLIENT_SECRET в файле .env\n", file=sys.stderr)
            sys.exit(1)
            
        except GigaChatAPIError as e:
            logger.error(f"Ошибка API: {e}")
            print(f"\nОшибка при запросе к GigaChat API: {e}\n", file=sys.stderr)
            sys.exit(1)
            
        except GigaChatError as e:
            logger.error(f"Ошибка GigaChat: {e}")
            print(f"\nОшибка: {e}\n", file=sys.stderr)
            sys.exit(1)
            
        except KeyboardInterrupt:
            logger.info("Прервано пользователем")
            print("\n\nПрервано пользователем.\n", file=sys.stderr)
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
            print(f"\nНеожиданная ошибка: {e}\n", file=sys.stderr)
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

