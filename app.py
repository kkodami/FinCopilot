import asyncio
import logging
from main import FinCopilotBot
from services.sheets_service import GoogleSheetsService
from services.llm_service import LLMService
from config import Config
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        credentials_path = Config.GOOGLE_CREDENTIALS_FILE

        # Проверяем существование файла
        if not credentials_path or not os.path.exists(credentials_path):
            logger.error("❌ Google credentials file not found!")
            return
        
        # Инициализация сервисов
        sheets_service = GoogleSheetsService(
            credentials_file=credentials_path,
            spreadsheet_id=Config.SPREADSHEET_ID
        )
        
        llm_service = LLMService(
            model=Config.LLM_MODEL,
            api_key=Config.OPENROUTER_API_KEY or Config.OPENAI_API_KEY
        )

        bot = FinCopilotBot(Config.BOT_TOKEN, sheets_service, llm_service)
        await bot.start()

    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())