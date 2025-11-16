import gspread
from google.oauth2.service_account import Credentials
from config import config
from models.transaction import Transaction
from models.budget import Budget
import os
from datetime import datetime, timedelta
import logging
import uuid

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
            # Лист транзакций
            try:
                worksheet = self.sheet.worksheet("Transactions")
            except:
                worksheet = self.sheet.add_worksheet(title="Transactions", rows="1000", cols="10")
            
            headers = [
                "uuid", "date", "type", "category", "subcategory",
                "amount", "currency", "description", "source", "created_at"
            ]
            worksheet.clear()
            worksheet.append_row(headers)
            
            # Лист бюджетов
            try:
                budget_ws = self.sheet.worksheet("Budgets")
            except:
                budget_ws = self.sheet.add_worksheet(title="Budgets", rows="100", cols="6")
            
            budget_headers = [
                "user_id", "category", "amount", "period", "created_at", "updated_at"
            ]
            budget_ws.clear()
            budget_ws.append_row(budget_headers)
            
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
    
    async def get_financial_stats(self, period: str, start_date: str = None, end_date: str = None):
        """Получает финансовую статистику за период"""
        try:
            # Определяем период
            if period == "custom" and start_date and end_date:
                # Используем переданные даты
                pass
            else:
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
    
    async def search_transactions(self, query: str, user_id: int = None):
        """Поиск транзакций по описанию и категории"""
        transactions = await self.get_transactions()
        results = []
        
        query_lower = query.lower()
        for t in transactions:
            description = t.get('description', '').lower()
            category = t.get('category', '').lower()
            
            if (query_lower in description or 
                query_lower in category or 
                query_lower in str(t.get('amount', '')).lower()):
                results.append(t)
        
        return results
    
    async def get_transactions_by_period(self, start_date: str, end_date: str):
        """Получает транзакции за произвольный период"""
        return await self.get_transactions(start_date, end_date)
    
    async def set_budget(self, budget: Budget):
        """Устанавливает бюджет для категории"""
        worksheet = self.sheet.worksheet("Budgets")
        
        # Проверяем существующий бюджет
        try:
            records = worksheet.get_all_records()
            for i, record in enumerate(records, start=2):
                if (record['user_id'] == budget.user_id and 
                    record['category'] == budget.category and 
                    record['period'] == budget.period):
                    # Обновляем существующий
                    worksheet.update_cell(i, 3, budget.amount)  # amount
                    worksheet.update_cell(i, 6, budget.updated_at)  # updated_at
                    return True
        except:
            pass
        
        # Создаем новый
        row = [
            budget.user_id,
            budget.category,
            budget.amount,
            budget.period,
            budget.created_at,
            budget.updated_at
        ]
        worksheet.append_row(row)
        return True
    
    async def get_budgets(self, user_id: int):
        """Получает бюджеты пользователя"""
        try:
            worksheet = self.sheet.worksheet("Budgets")
            records = worksheet.get_all_records()
            return [r for r in records if r['user_id'] == user_id]
        except:
            return []
    
    async def get_budget_status(self, user_id: int, period: str = "month"):
        """Получает статус бюджетов с анализом перерасходов"""
        budgets = await self.get_budgets(user_id)
        stats = await self.get_financial_stats(period)
        
        status = []
        for budget in budgets:
            category = budget['category']
            budget_amount = float(budget['amount'])
            
            # Сумма расходов по категории
            expense_amount = stats.get('expense_by_category', {}).get(category, 0)
            
            status.append({
                'category': category,
                'budget': budget_amount,
                'spent': expense_amount,
                'remaining': budget_amount - expense_amount,
                'overspent': expense_amount > budget_amount
            })
        
        return status
    
    async def edit_transaction(self, transaction_uuid: str, updates: dict):
        """Редактирует транзакцию"""
        worksheet = self.sheet.worksheet("Transactions")
        
        try:
            # Находим транзакцию
            cell = worksheet.find(transaction_uuid)
            row = cell.row
            headers = worksheet.row_values(1)
            
            for key, value in updates.items():
                if key in headers:
                    col_idx = headers.index(key) + 1
                    worksheet.update_cell(row, col_idx, value)
            
            return True
        except Exception as e:
            logger.error(f"Error editing transaction: {e}")
            return False
    
    async def delete_transaction(self, transaction_uuid: str):
        """Удаляет транзакцию"""
        worksheet = self.sheet.worksheet("Transactions")
        
        try:
            cell = worksheet.find(transaction_uuid)
            worksheet.delete_rows(cell.row)
            return True
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False