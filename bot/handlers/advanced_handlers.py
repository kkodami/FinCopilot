from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.google_sheets import GoogleSheetsService
from services.openrouter import OpenRouterService
from models.budget import Budget
from datetime import datetime, timedelta
import re

router = Router()

class BudgetStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()
    waiting_for_period = State()

class EditStates(StatesGroup):
    waiting_for_transaction_id = State()
    waiting_for_edit_field = State()
    waiting_for_edit_value = State()

class SearchStates(StatesGroup):
    waiting_for_query = State()

class CustomPeriodStates(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()

@router.message(Command("budget"))
async def cmd_budget(message: Message, state: FSMContext):
    """Управление бюджетами"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Установить бюджет"), KeyboardButton(text="📈 Статус бюджетов")],
            [KeyboardButton(text="🗑️ Удалить бюджет"), KeyboardButton(text="📋 Список бюджетов")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("💰 Управление бюджетами:", reply_markup=keyboard)

@router.message(F.text == "📊 Установить бюджет")
async def set_budget_start(message: Message, state: FSMContext):
    await message.answer(
        "Выберите категорию для установки бюджета:\n\n"
        "💼 Доходы:\n• зарплата\n• услуги\n• прочее\n\n"
        "💸 Расходы:\n• маркетинг\n• аренда\n• продукты\n• транспорт\n• оборудование\n• услуги\n• развлечения\n• налоги\n• прочее",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(BudgetStates.waiting_for_category)

@router.message(BudgetStates.waiting_for_category)
async def process_budget_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.lower())
    await message.answer("💵 Введите сумму бюджета:")
    await state.set_state(BudgetStates.waiting_for_amount)

@router.message(BudgetStates.waiting_for_amount)
async def process_budget_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        await state.update_data(amount=amount)
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📅 Месячный"), KeyboardButton(text="📆 Недельный")],
                [KeyboardButton(text="📊 Дневной")]
            ],
            resize_keyboard=True
        )
        await message.answer("🕐 Выберите период бюджета:", reply_markup=keyboard)
        await state.set_state(BudgetStates.waiting_for_period)
    except ValueError:
        await message.answer("❌ Введите корректную сумму:")

@router.message(BudgetStates.waiting_for_period)
async def process_budget_period(message: Message, state: FSMContext):
    period_map = {
        "📅 месячный": "monthly",
        "📆 недельный": "weekly", 
        "📊 дневной": "daily"
    }
    
    period = period_map.get(message.text.lower(), "monthly")
    data = await state.get_data()
    
    budget = Budget(
        user_id=message.from_user.id,
        category=data['category'],
        amount=data['amount'],
        period=period
    )
    
    sheets = GoogleSheetsService()
    await sheets.set_budget(budget)
    
    await message.answer(
        f"✅ Бюджет установлен!\n\n"
        f"Категория: {data['category']}\n"
        f"Сумма: {data['amount']} руб\n"
        f"Период: {period}",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

@router.message(F.text == "📈 Статус бюджетов")
async def show_budget_status(message: Message):
    sheets = GoogleSheetsService()
    status = await sheets.get_budget_status(message.from_user.id)
    
    if not status:
        await message.answer("📊 Бюджеты не установлены")
        return
    
    text = "📊 Статус бюджетов:\n\n"
    overspent_categories = []
    
    for item in status:
        emoji = "🔴" if item['overspent'] else "🟢"
        text += f"{emoji} {item['category'].title()}:\n"
        text += f"   Бюджет: {item['budget']:.2f} руб\n"
        text += f"   Потрачено: {item['spent']:.2f} руб\n"
        text += f"   Остаток: {item['remaining']:.2f} руб\n\n"
        
        if item['overspent']:
            overspent_categories.append(item['category'])
    
    if overspent_categories:
        text += f"⚠️ Перерасход в категориях: {', '.join(overspent_categories)}"
    
    await message.answer(text)

@router.message(Command("search"))
@router.message(F.text.contains("поиск"))
async def cmd_search(message: Message, state: FSMContext):
    """Поиск транзакций"""
    await message.answer("🔍 Введите запрос для поиска (категория, описание, сумма):")
    await state.set_state(SearchStates.waiting_for_query)

@router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    sheets = GoogleSheetsService()
    results = await sheets.search_transactions(message.text, message.from_user.id)
    
    if not results:
        await message.answer("❌ По вашему запросу ничего не найдено")
        await state.clear()
        return
    
    text = f"🔍 Найдено {len(results)} записей:\n\n"
    for i, transaction in enumerate(results[:10], 1):  # Ограничиваем 10 результатами
        type_emoji = "💰" if transaction.get('type') in ['income', 'доход'] else "💸"
        text += f"{i}. {type_emoji} {transaction.get('date', '')} - {transaction.get('amount', 0)} руб\n"
        text += f"   {transaction.get('category', '')} - {transaction.get('description', '')}\n\n"
    
    await message.answer(text)
    await state.clear()

@router.message(Command("period"))
async def cmd_custom_period(message: Message, state: FSMContext):
    """Отчет за произвольный период"""
    await message.answer("📅 Введите начальную дату в формате ГГГГ-ММ-ДД:")
    await state.set_state(CustomPeriodStates.waiting_for_start_date)

@router.message(CustomPeriodStates.waiting_for_start_date)
async def process_start_date(message: Message, state: FSMContext):
    if not re.match(r'\d{4}-\d{2}-\d{2}', message.text):
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД:")
        return
    
    await state.update_data(start_date=message.text)
    await message.answer("📅 Введите конечную дату в формате ГГГГ-ММ-ДД:")
    await state.set_state(CustomPeriodStates.waiting_for_end_date)

@router.message(CustomPeriodStates.waiting_for_end_date)
async def process_end_date(message: Message, state: FSMContext):
    if not re.match(r'\d{4}-\d{2}-\d{2}', message.text):
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД:")
        return
    
    data = await state.get_data()
    start_date = data['start_date']
    end_date = message.text
    
    try:
        sheets = GoogleSheetsService()
        openrouter = OpenRouterService()
        
        stats = await sheets.get_financial_stats("custom", start_date, end_date)
        report = await openrouter.generate_report(stats, f"период {start_date} - {end_date}")
        
        await message.answer(report)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации отчета: {str(e)}")
    
    await state.clear()

@router.message(Command("fix"))
async def cmd_fix(message: Message):
    """Анализ и исправление финансовых проблем"""
    sheets = GoogleSheetsService()
    openrouter = OpenRouterService()
    
    try:
        # Получаем последние транзакции для анализа
        transactions = await sheets.get_transactions()
        budgets_status = await sheets.get_budget_status(message.from_user.id)
        
        # Анализируем перерасходы
        overspent = [item for item in budgets_status if item['overspent']]
        
        if overspent:
            text = "⚠️ Обнаружены перерасходы:\n\n"
            for item in overspent:
                text += f"🔴 {item['category']}: превышение на {abs(item['remaining']):.2f} руб\n"
            text += "\n💡 Рекомендуется сократить расходы в этих категориях."
        else:
            text = "✅ Перерасходов не обнаружено. Финансы в порядке!"
        
        # Добавляем AI-рекомендации
        insights = await openrouter.generate_insights(transactions[-20:])
        text += f"\n\n{insights}"
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка анализа: {str(e)}")

@router.message(Command("export"))
async def cmd_export(message: Message):
    """Экспорт данных (заглушка для PDF)"""
    await message.answer(
        "📤 Функция экспорта в PDF находится в разработке.\n\n"
        "Сейчас вы можете использовать:\n"
        "• Скриншоты отчетов\n" 
        "• Копирование данных из поиска\n"
        "• Ручное сохранение важной информации"
    )

@router.message(Command("top"))
async def cmd_top(message: Message):
    """Топ расходов/доходов"""
    sheets = GoogleSheetsService()
    stats = await sheets.get_financial_stats("month")
    
    # Топ расходов по категориям
    expenses = stats.get('expense_by_category', {})
    if expenses:
        top_expenses = sorted(expenses.items(), key=lambda x: x[1], reverse=True)[:5]
        text = "🔥 Топ расходов за месяц:\n\n"
        for category, amount in top_expenses:
            text += f"• {category}: {amount:.2f} руб\n"
    else:
        text = "📊 Расходы за месяц не найдены"
    
    # Топ доходов по категориям
    incomes = stats.get('income_by_category', {})
    if incomes:
        top_incomes = sorted(incomes.items(), key=lambda x: x[1], reverse=True)[:5]
        text += "\n💰 Топ доходов за месяц:\n\n"
        for category, amount in top_incomes:
            text += f"• {category}: {amount:.2f} руб\n"
    
    await message.answer(text)

@router.message(F.text == "📋 Список бюджетов")
async def show_budgets_list(message: Message):
    sheets = GoogleSheetsService()
    budgets = await sheets.get_budgets(message.from_user.id)
    
    if not budgets:
        await message.answer("📊 Бюджеты не установлены")
        return
    
    text = "📋 Ваши бюджеты:\n\n"
    for budget in budgets:
        text += f"• {budget['category']}: {budget['amount']} руб ({budget['period']})\n"
    
    await message.answer(text)

@router.message(F.text == "🗑️ Удалить бюджет")
async def delete_budget_start(message: Message):
    sheets = GoogleSheetsService()
    budgets = await sheets.get_budgets(message.from_user.id)
    
    if not budgets:
        await message.answer("📊 Бюджеты не установлены")
        return
    
    text = "🗑️ Выберите бюджет для удаления:\n\n"
    keyboard_buttons = []
    
    for budget in budgets:
        button_text = f"{budget['category']} - {budget['amount']} руб"
        keyboard_buttons.append([KeyboardButton(text=button_text)])
    
    keyboard_buttons.append([KeyboardButton(text="❌ Отмена")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
    await message.answer(text, reply_markup=keyboard)