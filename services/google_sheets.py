import gspread
from google.oauth2.service_account import Credentials
from config import config
from models.transaction import Transaction

class GoogleSheetsService:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = Credentials.from_service_account_file(
            config.GOOGLE_SHEETS_CREDENTIALS, scopes=self.scope
        )
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
        # Здесь можно добавить сложную логику агрегации
        transactions = await self.get_transactions()
        
        incomes = [t for t in transactions if t['type'] == 'income']
        expenses = [t for t in transactions if t['type'] == 'expense']
        
        return {
            'total_income': sum(t['amount'] for t in incomes),
            'total_expense': sum(t['amount'] for t in expenses),
            'profit': sum(t['amount'] for t in incomes) - sum(t['amount'] for t in expenses),
            'transactions_count': len(transactions),
            'incomes': incomes,
            'expenses': expenses
        }