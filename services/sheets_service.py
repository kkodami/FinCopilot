import gspread
from google.oauth2.service_account import Credentials

class GoogleSheetsService:
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_file = credentials_file
        self.client = self._authenticate()
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        
        # Создаем лист если его нет
        self.transactions_sheet = self._get_or_create_worksheet("Transactions")
        
        # Создаем заголовки если их нет
        self._ensure_headers()
    
    def _authenticate(self):
        """Аутентификация в Google Sheets API"""
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
        return gspread.authorize(creds)
    
    def _get_or_create_worksheet(self, title: str):
        """Получить существующий лист или создать новый"""
        try:
            return self.spreadsheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            # Создаем новый лист
            worksheet = self.spreadsheet.add_worksheet(title=title, rows="1000", cols="10")
            print(f"✅ Создан новый лист: {title}")
            return worksheet
    
    def _ensure_headers(self):
        """Создаем заголовки столбцов если их нет"""
        headers = ["Date", "Amount", "Category", "Description", "User"]
        current_data = self.transactions_sheet.get_all_values()
        
        if not current_data:  # Если лист пустой
            self.transactions_sheet.append_row(headers)
            print("✅ Заголовки столбцов созданы")
    
    async def add_transaction(self, data: dict):
        """Добавление транзакции в таблицу"""
        try:
            row = [
                data.get('date', ''),
                data.get('amount', ''),
                data.get('category', ''),
                data.get('description', ''),
                data.get('user', '')
            ]
            self.transactions_sheet.append_row(row)
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления транзакции: {e}")
            return False
    
    async def get_transactions(self, limit: int = 10):
        """Получение последних транзакций"""
        try:
            records = self.transactions_sheet.get_all_records()
            return records[-limit:] if records else []
        except Exception as e:
            print(f"❌ Ошибка получения транзакций: {e}")
            return []
    
        
        
    