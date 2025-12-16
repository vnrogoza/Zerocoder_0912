"""
Простая обертка для запуска GigaChat CLI.
Позволяет запускать команду напрямую: python main_bot.py summary --text "текст"
или 
python main_bot.py summary --file bot/messages.txt
python main_bot.py summary --file bot/turgenev.txt


pip install -r requirements.txt
"""

import sys

# CLI-выжимка
from bot.main import main as cli_main

# Telegram-бот
from bot.main_telebot import main as telebot_main

if __name__ == '__main__':
    # Раскомментируйте нужный запуск
    # cli_main()
    telebot_main()

