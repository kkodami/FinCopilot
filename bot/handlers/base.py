from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

# Импортируем функции из других модулей
from bot.handlers.advanced_handlers import cmd_budget, cmd_search, cmd_top
from bot.handlers.reports import cmd_insights

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    # Основная клавиатура
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💸 Добавить операцию"), KeyboardButton(text="📊 Отчет")],
            [KeyboardButton(text="💰 Бюджеты"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="💡 Аналитика"), KeyboardButton(text="📈 Топ операций")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "🤖 Добро пожаловать в FinCopilot!\n\n"
        "Я помогу вам вести финансовый учет и анализировать ваши доходы/расходы.\n\n"
        "📱 Используйте кнопки ниже или команды:\n\n"
        "💸 Добавление операций:\n"
        "• Просто напишите: \"доход/расход сумма описание\"\n"
        "• Или нажмите \"💸 Добавить операцию\"\n\n"
        "📊 Отчеты и аналитика:\n"
        "• /report - полный отчет\n"
        "• /profit - прибыль\n"
        "• /top - топ операций\n"
        "• /period - отчет за период\n\n"
        "💰 Управление бюджетами:\n"
        "• /budget - настройка бюджетов\n"
        "• /fix - анализ проблем\n\n"
        "🔍 Поиск и редактирование:\n"
        "• /search - поиск операций\n"
        "• /help - полная справка",
        reply_markup=keyboard
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 Полный список команд:\n\n"
        "💸 Добавление операций:\n"
        "/add - добавить операцию\n"
        "Просто напишите: \"доход 50000 зарплата\"\n\n"
        "📊 Отчеты:\n"
        "/report - полный отчет\n"
        "/profit - прибыль и убытки\n"
        "/month - за месяц\n"
        "/week - за неделю\n"
        "/period - за произвольный период\n"
        "/top - топ операций\n\n"
        "💰 Бюджеты:\n"
        "/budget - управление бюджетами\n"
        "/fix - анализ перерасходов\n\n"
        "🔍 Поиск и анализ:\n"
        "/search - поиск операций\n"
        "/insights - AI-аналитика\n"
        "/export - экспорт данных\n\n"
        "⚙️ Профиль:\n"
        "/profile - профиль\n"
        "/status - статус системы"
    )

@router.message(Command("insights"))
async def cmd_insights_handler(message: Message):
    """Показывает аналитические инсайты"""
    await cmd_insights(message)

# Обработчики кнопок - исправлены ошибки
@router.message(F.text == "💸 Добавить операцию")
async def add_transaction_btn(message: Message):
    await message.answer(
        "💸 Введите операцию в формате:\n\n"
        "• <b>Доход:</b> \"доход 50000 зарплата\"\n"
        "• <b>Расход:</b> \"расход 2500 обед в кафе\"\n\n"
        "Или используйте категории:\n"
        "• маркетинг, аренда, продукты, транспорт\n"
        "• оборудование, услуги, развлечения, налоги",
        parse_mode="HTML"
    )

@router.message(F.text == "📊 Отчет")
async def report_btn(message: Message):
    await message.answer(
        "📊 Выберите тип отчета:\n\n"
        "/report - полный отчет\n"
        "/profit - прибыль\n" 
        "/month - за месяц\n"
        "/week - за неделю\n"
        "/period - за период\n"
        "/top - топ операций"
    )

@router.message(F.text == "💰 Бюджеты")
async def budgets_btn(message: Message):
    from aiogram.fsm.context import FSMContext
    # Создаем контекст состояния
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=None)
    await cmd_budget(message, state)

@router.message(F.text == "🔍 Поиск")
async def search_btn(message: Message):
    from aiogram.fsm.context import FSMContext
    # Создаем контекст состояния
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=None)
    await cmd_search(message, state)

@router.message(F.text == "💡 Аналитика")
async def analytics_btn(message: Message):
    await cmd_insights(message)

@router.message(F.text == "📈 Топ операций")
async def top_btn(message: Message):
    await cmd_top(message)