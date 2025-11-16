import gspread
from google.oauth2.service_account import Credentials
from typing import Optional, Dict, Any
from config import config
from models.user import User
from services.provisioning import OpenRouterProvisioningService
import datetime

class UserManager:
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = Credentials.from_service_account_file(
            config.GOOGLE_SHEETS_CREDENTIALS, scopes=self.scope
        )
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(config.SPREADSHEET_ID)
        self.provisioning = OpenRouterProvisioningService()
    
    async def get_or_create_user(self, user_id: int, username: str, first_name: str, last_name: str = None) -> User:
        """Получает или создает пользователя"""
        worksheet = self.sheet.worksheet("Users")
        
        # Ищем существующего пользователя
        try:
            records = worksheet.get_all_records()
            for record in records:
                if record['user_id'] == user_id:
                    return User(
                        user_id=user_id,
                        username=record.get('username'),
                        first_name=record['first_name'],
                        last_name=record.get('last_name'),
                        openrouter_key=record.get('openrouter_key'),
                        key_hash=record.get('key_hash'),
                        credit_limit=float(record.get('credit_limit', 100)),
                        is_premium=bool(record.get('is_premium', False)),
                        created_at=record.get('created_at'),
                        last_activity=record.get('last_activity')
                    )
        except Exception:
            pass
        
        # Создаем нового пользователя
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        # Создаем API ключ для пользователя
        try:
            key_response = await self.provisioning.create_user_key(
                user_id=user_id,
                user_name=user.display_name,
                credit_limit=user.credit_limit
            )
            
            user.openrouter_key = key_response['key']
            user.key_hash = key_response['hash']
            
        except Exception as e:
            # Если не удалось создать ключ, используем общий
            user.openrouter_key = config.OPENROUTER_API_KEY
        
        # Сохраняем пользователя в Google Sheets
        row = [
            user.user_id,
            user.username or "",
            user.first_name,
            user.last_name or "",
            user.openrouter_key or "",
            user.key_hash or "",
            user.credit_limit,
            user.is_premium,
            user.created_at,
            datetime.now().isoformat()
        ]
        
        worksheet.append_row(row)
        return user
    
    async def update_user_activity(self, user_id: int):
        """Обновляет время последней активности"""
        worksheet = self.sheet.worksheet("Users")
        
        try:
            cell = worksheet.find(str(user_id))
            worksheet.update_cell(cell.row, 10, datetime.now().isoformat())  # last_activity колонка
        except Exception:
            pass
    
    async def get_user_usage(self, user_id: int) -> Dict[str, float]:
        """Получает информацию об использовании API пользователем"""
        user = await self.get_or_create_user(user_id, "", "")  # Заглушки, т.к. пользователь уже должен существовать
        
        if user.key_hash:
            return await self.provisioning.get_key_usage(user.key_hash)
        
        return {"error": "No dedicated API key"}