from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.sheets_service import GoogleSheetsService
from services.llm_service import LLMService
from services.parser_service import TransactionParser

router = Router()

# Состояния для FSM
class TransactionStates(StatesGroup):
    waiting_for_transaction = State()

def register_handlers(dp, sheets_service: GoogleSheetsService, llm_service: LLMService):
    dp.include_router(router)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🚀 Бот запущен! Google Sheets подключен!")

@router.message(Command("test"))
async def cmd_test(message: Message):
    await message.answer("✅ Бот работает корректно!")

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await message.answer("💬 Опишите транзакцию:\n\nПример: 'Расход 2500 рублей на контекстную рекламу сегодня'")
    await state.set_state(TransactionStates.waiting_for_transaction)

@router.message(Command("report"))
async def cmd_report(message: Message):
    await message.answer("📊 Выберите период:\n/week - за неделю\n/month - за месяц\n/quarter - за квартал")

@router.message(Command("profit"))
async def cmd_profit(message: Message, sheets_service: GoogleSheetsService):
    """Получение и расчет прибыли"""
    try:
        profit_data = await calculate_profit(sheets_service)
        await message.answer(f"💰 Прибыль: {profit_data} руб")
    except Exception as e:
        await message.answer("❌ Ошибка при расчете прибыли")

@router.message(F.text)
async def handle_transaction(message: Message, sheets_service: GoogleSheetsService, llm_service: LLMService):
    """Обработка транзакций в свободной форме"""
    try:
        # Парсинг транзакции
        parser = TransactionParser(llm_service)
        transaction_data = await parser.parse_transaction(message.text)
        
        if transaction_data:
            # Добавление в Google Sheets
            success = await sheets_service.add_transaction(transaction_data)
            if success:
                await message.answer("✅ Транзакция добавлена!")
            else:
                await message.answer("❌ Ошибка при сохранении")
        else:
            await message.answer("❌ Не удалось распознать транзакцию")
            
    except Exception as e:
        await message.answer("⚠️ Произошла ошибка при обработке")

@router.message(TransactionStates.waiting_for_transaction)
async def handle_transaction_state(message: Message, state: FSMContext, sheets_service: GoogleSheetsService, llm_service: LLMService):
    """Обработка транзакции из состояния FSM"""
    try:
        # Парсинг транзакции
        parser = TransactionParser(llm_service)
        transaction_data = await parser.parse_transaction(message.text)
        
        if transaction_data:
            # Добавление в Google Sheets
            success = await sheets_service.add_transaction(transaction_data)
            if success:
                response = (
                    "✅ Транзакция добавлена!\n\n"
                    f"💵 Сумма: {transaction_data.get('amount', '')} {transaction_data.get('currency', 'RUB')}\n"
                    f"📁 Тип: {transaction_data.get('type', '')}\n"
                    f"📝 Описание: {transaction_data.get('description', '')}"
                )
                await message.answer(response)
            else:
                await message.answer("❌ Ошибка при сохранении")
        else:
            await message.answer("❌ Не удалось распознать транзакцию")
            
    except Exception as e:
        await message.answer("⚠️ Произошла ошибка при обработке")
    
    await state.clear()

# Функция для расчета прибыли
async def calculate_profit(sheets_service: GoogleSheetsService) -> float:
    """Расчет общей прибыли из транзакций"""
    try:
        transactions = await sheets_service.get_transactions(limit=1000)
        
        total_income = 0
        total_expenses = 0
        
        for transaction in transactions:
            amount = float(transaction.get('Amount', 0))
            category = transaction.get('Category', '').lower()
            description = transaction.get('Description', '').lower()
            
            # Определяем тип операции
            if any(keyword in category or keyword in description 
                   for keyword in ['доход', 'прибыль', 'заработок', 'income']):
                total_income += amount
            elif any(keyword in category or keyword in description 
                     for keyword in ['расход', 'трата', 'покупка', 'expense']):
                total_expenses += amount
        
        profit = total_income - total_expenses
        return profit
        
    except Exception as e:
        print(f"❌ Ошибка расчета прибыли: {e}")
        return 0.0