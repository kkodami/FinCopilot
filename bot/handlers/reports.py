from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from services.google_sheets import GoogleSheetsService
from services.openrouter import OpenRouterService

router = Router()

@router.message(Command("report"))
@router.message(F.text.lower().contains("отчет"))
async def generate_report(message: Message):
    """Генерирует финансовый отчет"""
    
    try:
        sheets = GoogleSheetsService()
        openrouter = OpenRouterService()
        
        # Получаем данные за последний месяц
        stats = await sheets.get_financial_stats("month")
        
        # Генерируем отчет с помощью LLM
        report = await openrouter.generate_report(stats, "последний месяц")
        
        await message.answer(report)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации отчета: {str(e)}")

@router.message(Command("profit"))
@router.message(F.text.lower().contains("прибыль"))
async def show_profit(message: Message):
    """Показывает прибыль за период"""
    
    try:
        sheets = GoogleSheetsService()
        stats = await sheets.get_financial_stats("month")
        
        profit = stats['profit']
        profit_emoji = "📈" if profit > 0 else "📉" if profit < 0 else "➡️"
        
        await message.answer(
            f"💰 Прибыль за последний месяц:\n"
            f"• Доходы: {stats['total_income']:.2f} руб\n"
            f"• Расходы: {stats['total_expense']:.2f} руб\n"
            f"• {profit_emoji} Прибыль: {profit:.2f} руб\n"
            f"• Рентабельность: {(profit/stats['total_income']*100 if stats['total_income'] > 0 else 0):.1f}%"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("month"))
async def monthly_report(message: Message):
    """Отчет за текущий месяц"""
    try:
        sheets = GoogleSheetsService()
        openrouter = OpenRouterService()
        
        stats = await sheets.get_financial_stats("month")
        report = await openrouter.generate_report(stats, "текущий месяц")
        
        await message.answer(report)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("week"))
async def weekly_report(message: Message):
    """Отчет за неделю"""
    try:
        sheets = GoogleSheetsService()
        openrouter = OpenRouterService()
        
        stats = await sheets.get_financial_stats("week")
        report = await openrouter.generate_report(stats, "последнюю неделю")
        
        await message.answer(report)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")