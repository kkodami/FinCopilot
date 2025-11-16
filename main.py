from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from services.sheets_service import GoogleSheetsService
from services.llm_service import LLMService
from services.parser_service import TransactionParser

from middlewares.dependency import DependencyMiddleware

class FinCopilotBot:
    def __init__(self, token: str, sheets_service: GoogleSheetsService, llm_service: LLMService):
        # Создаем бота с настройками по умолчанию
        self.bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Создаем хранилище для FSM
        self.storage = MemoryStorage()
        
        # Создаем диспетчер БЕЗ передачи бота
        self.dp = Dispatcher(storage=self.storage)
        
        self.sheets_service = sheets_service
        self.llm_service = llm_service
        
        # Регистрируем обработчики
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация всех обработчиков"""
        from handlers import register_handlers
        register_handlers(self.dp, self.sheets_service, self.llm_service)

    def _register_handlers(self):
        from handlers import register_handlers
        
        # добавляем зависимости в контекст aiogram
        self.dp.message.middleware(DependencyMiddleware(self.sheets_service, self.llm_service))
        
        register_handlers(self.dp, self.sheets_service, self.llm_service)
    
    async def start(self):
        """Запуск бота"""
        print("🤖 Бот запускается...")
        
        # Удаляем вебхук (если был) и запускаем polling
        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)