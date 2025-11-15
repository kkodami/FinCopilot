import asyncio
import logging
from main import FinCopilotBot
from services.sheets_service import GoogleSheetsService
from services.llm_service import LLMService
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация сервисов
        sheets_service = GoogleSheetsService(
            Config.GOOGLE_CREDENTIALS_FILE,
            Config.SPREADSHEET_ID
        )
        
        llm_service = LLMService()  # Или ваша реализация
        
        # Создание и запуск бота
        bot = FinCopilotBot(Config.BOT_TOKEN, sheets_service, llm_service)
        await bot.start()  # ⬅️ Используем start() вместо run()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())