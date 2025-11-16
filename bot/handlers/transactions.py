from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.openrouter import OpenRouterService
from services.google_sheets import GoogleSheetsService
from models.transaction import Transaction

router = Router()

class AddTransaction(StatesGroup):
    waiting_for_text = State()

@router.message(F.text.lower().startswith(('доход', 'расход', 'приход', 'трата', 'затрата')))
async def handle_transaction_message(message: Message):
    """Обрабатывает сообщения о транзакциях в свободной форме"""
    
    try:
        # Парсим текст с помощью OpenRouter
        openrouter = OpenRouterService()
        parsed_data = await openrouter.parse_transaction(message.text)
        
        # Создаем транзакцию
        transaction = Transaction.create_from_text(message.text, parsed_data)
        
        # Сохраняем в Google Sheets
        sheets = GoogleSheetsService()
        await sheets.add_transaction(transaction)
        
        await message.answer(
            f"✅ Запись добавлена!\n"
            f"Тип: {transaction.type}\n"
            f"Сумма: {transaction.amount} {transaction.currency}\n"
            f"Категория: {transaction.category}\n"
            f"Описание: {transaction.description}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(AddTransaction.waiting_for_text)
async def process_transaction_text(message: Message, state: FSMContext):
    """Обрабатывает текст транзакции из состояния"""
    try:
        openrouter = OpenRouterService()
        parsed_data = await openrouter.parse_transaction(message.text)
        
        transaction = Transaction.create_from_text(message.text, parsed_data)
        sheets = GoogleSheetsService()
        await sheets.add_transaction(transaction)
        
        await message.answer(
            f"✅ Запись добавлена!\n"
            f"Тип: {transaction.type}\n"
            f"Сумма: {transaction.amount} {transaction.currency}\n"
            f"Категория: {transaction.category}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        await state.clear()