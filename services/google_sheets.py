import gspread
from google.oauth2.service_account import Credentials
from config import config
from models.transaction import Transaction
import os
from datetime import datetime, timedelta

class GoogleSheetsService:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds_path = config.GOOGLE_SHEETS_CREDENTIALS
        if not creds_path:
            raise RuntimeError(
                "GOOGLE_SHEETS_CREDENTIALS не задан. Установите в .env путь к JSON сервисного аккаунта."
            )
        if not os.path.exists(creds_path):
            raise RuntimeError(f"Файл учетных данных Google не найден: {creds_path}")
        self.creds = Credentials.from_service_account_file(creds_path, scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(config.SPREADSHEET_ID)
    
    async def add_transaction(self, transaction: Transaction):
        """Добавляет транзакцию в Google Sheets"""
        worksheet = self.sheet.worksheet("Transactions")
        
        row = [
            transaction.uuid,
            transaction.date,
            transaction.type,
            transaction.category,
            transaction.subcategory or "",
            transaction.amount,
            transaction.currency,
            transaction.description,
            transaction.source,
            transaction.created_at
        ]
        
        worksheet.append_row(row)
    
    async def get_transactions(self, start_date: str = None, end_date: str = None):
        """Получает транзакции за период"""
        worksheet = self.sheet.worksheet("Transactions")
        records = worksheet.get_all_records()
        
        if start_date and end_date:
            records = [r for r in records if start_date <= r['date'] <= end_date]
        
        return records
    
    async def get_categories(self):
        """Получает список категорий"""
        worksheet = self.sheet.worksheet("Categories")
        return worksheet.get_all_records()
    
    async def get_financial_stats(self, period: str):
        """Получает финансовую статистику за период"""
        # Определяем период
        end_date = datetime.now().strftime('%Y-%m-%d')
        if period == "month":
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif period == "week":
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        else:
            # По умолчанию за все время
            start_date = "2000-01-01"
        
        transactions = await self.get_transactions(start_date, end_date)
        
        incomes = [t for t in transactions if t.get('type') == 'income']
        expenses = [t for t in transactions if t.get('type') == 'expense']
        
        # Группируем по категориям
        income_by_category = {}
        expense_by_category = {}
        
        for t in incomes:
            category = t.get('category', 'прочее')
            income_by_category[category] = income_by_category.get(category, 0) + float(t.get('amount', 0))
        
        for t in expenses:
            category = t.get('category', 'прочее')
            expense_by_category[category] = expense_by_category.get(category, 0) + float(t.get('amount', 0))
        
        return {
            'total_income': sum(float(t.get('amount', 0)) for t in incomes),
            'total_expense': sum(float(t.get('amount', 0)) for t in expenses),
            'profit': sum(float(t.get('amount', 0)) for t in incomes) - sum(float(t.get('amount', 0)) for t in expenses),
            'transactions_count': len(transactions),
            'income_by_category': income_by_category,
            'expense_by_category': expense_by_category,
            'incomes': incomes,
            'expenses': expenses
        }