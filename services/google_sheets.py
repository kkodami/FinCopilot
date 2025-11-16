import gspread
from google.oauth2.service_account import Credentials
from config import config
from models.transaction import Transaction
import os
from datetime import datetime, timedelta
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

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
        """Добавляет транзакцию в Google Sheets с правильной структурой"""
        worksheet = self.sheet.worksheet("Transactions")
        
        # Проверяем и создаем заголовки если нужно
        try:
            current_headers = worksheet.row_values(1)
            expected_headers = [
                "uuid", "date", "type", "category", "subcategory", 
                "amount", "currency", "description", "source", "created_at"
            ]
            
            if not current_headers or current_headers != expected_headers:
                worksheet.clear()
                worksheet.append_row(expected_headers)
        except Exception as e:
            logger.error(f"Error checking headers: {e}")
            # Создаем новую таблицу с заголовками
            worksheet.clear()
            worksheet.append_row(expected_headers)
        
        # Данные в ТОЧНОМ порядке заголовков
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
    
    async def initialize_sheet_structure(self):
        """Инициализирует правильную структуру таблицы"""
        try:
            worksheet = self.sheet.worksheet("Transactions")
            
            # Очищаем и создаем правильные заголовки
            worksheet.clear()
            
            headers = [
                "uuid", "date", "type", "category", "subcategory",
                "amount", "currency", "description", "source", "created_at"
            ]
            
            worksheet.append_row(headers)
            logger.info("Sheet structure initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing sheet: {e}")
            return False
    
    async def get_transactions(self, start_date: str = None, end_date: str = None):
        """Получает транзакции за период"""
        worksheet = self.sheet.worksheet("Transactions")
        
        try:
            # Получаем все данные
            data = worksheet.get_all_values()
            
            if len(data) <= 1:  # Только заголовки или пусто
                return []
            
            # Извлекаем заголовки и делаем их уникальными
            headers = data[0]
            unique_headers = []
            header_count = {}
            
            for header in headers:
                if header in header_count:
                    header_count[header] += 1
                    unique_headers.append(f"{header}_{header_count[header]}")
                else:
                    header_count[header] = 1
                    unique_headers.append(header)
            
            # Создаем записи
            records = []
            for row in data[1:]:
                if len(row) < len(unique_headers):
                    # Дополняем строку пустыми значениями
                    row.extend([''] * (len(unique_headers) - len(row)))
                
                record = dict(zip(unique_headers, row[:len(unique_headers)]))
                records.append(record)
            
            # Фильтруем по дате если нужно
            if start_date and end_date:
                filtered_records = []
                for record in records:
                    record_date = record.get('date', '')
                    if start_date <= record_date <= end_date:
                        filtered_records.append(record)
                return filtered_records
            
            return records
            
        except Exception as e:
            logger.error(f"Error reading transactions: {e}")
            # Fallback: пытаемся прочитать без обработки заголовков
            try:
                return worksheet.get_all_records()
            except:
                return []
    
    async def get_financial_stats(self, period: str):
        """Получает финансовую статистику за период"""
        try:
            # Определяем период
            end_date = datetime.now().strftime('%Y-%m-%d')
            if period == "month":
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            elif period == "week":
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            else:
                start_date = "2000-01-01"
            
            transactions = await self.get_transactions(start_date, end_date)
            
            if not transactions:
                return self._get_empty_stats()
            
            # Обрабатываем транзакции
            incomes = []
            expenses = []

            for t in transactions:
                try:
                    trans_type = str(t.get('type', '')).strip().lower()
                    amount_str = t.get('amount', '0')
                    
                    # Преобразуем сумму в число
                    try:
                        amount = float(str(amount_str).replace(',', '.'))
                    except (ValueError, TypeError):
                        continue
                    
                    # Расширенная проверка типа транзакции
                    if any(income_word in trans_type for income_word in ['income', 'доход', 'приход']):
                        incomes.append({'amount': amount, 'category': t.get('category', 'прочее')})
                    elif any(expense_word in trans_type for expense_word in ['expense', 'расход', 'трата', 'затрата']):
                        expenses.append({'amount': amount, 'category': t.get('category', 'прочее')})
                    else:
                        # Если тип не распознан, логируем для отладки
                        logger.warning(f"Unknown transaction type: '{trans_type}' in transaction: {t}")
                        
                except Exception as e:
                    logger.warning(f"Error processing transaction: {e}, transaction: {t}")
                    continue
            
            # Группируем по категориям
            income_by_category = {}
            expense_by_category = {}
            
            for t in incomes:
                category = t.get('category', 'прочее')
                income_by_category[category] = income_by_category.get(category, 0) + t.get('amount', 0)
            
            for t in expenses:
                category = t.get('category', 'прочее')
                expense_by_category[category] = expense_by_category.get(category, 0) + t.get('amount', 0)
            
            total_income = sum(t.get('amount', 0) for t in incomes)
            total_expense = sum(t.get('amount', 0) for t in expenses)
            
            return {
                'total_income': total_income,
                'total_expense': total_expense,
                'profit': total_income - total_expense,
                'transactions_count': len(incomes) + len(expenses),
                'income_by_category': income_by_category,
                'expense_by_category': expense_by_category,
                'incomes': incomes,
                'expenses': expenses
            }
            
        except Exception as e:
            logger.error(f"Error in get_financial_stats: {e}")
            return self._get_empty_stats()
    
    def _get_empty_stats(self):
        """Возвращает пустую статистику"""
        return {
            'total_income': 0,
            'total_expense': 0,
            'profit': 0,
            'transactions_count': 0,
            'income_by_category': {},
            'expense_by_category': {},
            'incomes': [],
            'expenses': []
        }

