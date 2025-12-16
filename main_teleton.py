"""
Точка входа для запуска Telegram бота.
Позволяет запускать команду напрямую: 
python main_teleton.py
"""

import asyncio
from teleton.main import main

if __name__ == '__main__':
    asyncio.run(main())
