from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🤖 Добро пожаловать в FinCopilot!\n\n"
        "Я помогу вам вести финансовый учет и анализировать ваши доходы/расходы.\n\n"
        "Просто напишите мне в свободной форме:\n"
        "• \"расход 2500 на рекламу сегодня\"\n"
        "• \"доход 15000 за консультацию\"\n"
        "• \"трата 5000 аренда офиса\"\n\n"
        "Или используйте команды:\n"
        "/report - финансовый отчет\n"
        "/profit - прибыль за период\n"
        "/top - топ расходов\n"
        "/help - помощь"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 Доступные команды:\n\n"
        "💸 Добавление операций:\n"
        "• Просто напишите в чат: \"доход/расход сумма описание\"\n"
        "• Пример: \"расход 2500 реклама в инстаграм\"\n\n"
        "📊 Отчеты:\n"
        "/report - полный финансовый отчет\n"
        "/profit - прибыль и убытки\n"
        "/top - самые крупные расходы\n"
        "/month - отчет за месяц\n\n"
        "🔧 Другое:\n"
        "/help - эта справка\n"
        "/categories - список категорий"
    )

@router.message(Command("insights"))
async def cmd_insights(message: Message):
    """Показывает аналитические инсайты"""
    try:
        from services.google_sheets import GoogleSheetsService
        from services.openrouter import OpenRouterService
        
        sheets = GoogleSheetsService()
        openrouter = OpenRouterService()
        
        transactions = await sheets.get_transactions()
        insights = await openrouter.generate_insights(transactions)
        
        await message.answer(f"💡 Финансовые инсайты:\n\n{insights}")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации инсайтов: {str(e)}")