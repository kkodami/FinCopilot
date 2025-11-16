import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from bot.handlers import base, transactions, reports, user_management, advanced_handlers

async def main():
    logging.basicConfig(level=logging.INFO)
    
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем все роутеры
    dp.include_router(base.router)
    dp.include_router(transactions.router)
    dp.include_router(reports.router)
    dp.include_router(user_management.router)
    dp.include_router(advanced_handlers.router)  # Новый роутер с расширенной функциональностью
    
    # Инициализируем структуру таблицы при старте
    try:
        from services.google_sheets import GoogleSheetsService
        sheets = GoogleSheetsService()
        await sheets.initialize_sheet_structure()
        logging.info("Google Sheets structure initialized")
    except Exception as e:
        logging.warning(f"Could not initialize sheets structure: {e}")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())