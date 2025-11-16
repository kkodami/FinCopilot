import aiohttp
import json
from typing import List, Optional, Dict, Any
from config import config

class OpenRouterProvisioningService:
    def __init__(self):
        self.provisioning_key = config.OPENROUTER_PROVISIONING_KEY
        self.base_url = "https://openrouter.ai/api/v1/keys"
    
    async def _make_request(self, method: str, endpoint: str = "", data: Optional[Dict] = None) -> Dict:
        """Базовый метод для запросов к Provisioning API"""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers={
                    "Authorization": f"Bearer {self.provisioning_key}",
                    "Content-Type": "application/json"
                },
                json=data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Provisioning API error: {response.status} - {error_text}")
    
    async def create_user_key(self, user_id: int, user_name: str, credit_limit: float = 100) -> Dict[str, Any]:
        """Создает новый API ключ для пользователя"""
        
        key_data = {
            "name": f"FinCopilot User {user_id}: {user_name}",
            "limit": credit_limit,
            "limit_reset": "monthly"  # Сбрасывать лимит ежемесячно
        }
        
        response = await self._make_request("POST", "", key_data)
        return response
    
    async def list_user_keys(self, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает список API ключей"""
        response = await self._make_request("GET", f"?offset={offset}")
        return response.get("data", [])
    
    async def get_user_key(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о конкретном ключе"""
        try:
            response = await self._make_request("GET", key_hash)
            return response.get("data")
        except Exception:
            return None
    
    async def update_user_key(self, key_hash: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет настройки ключа"""
        response = await self._make_request("PATCH", key_hash, updates)
        return response
    
    async def disable_user_key(self, key_hash: str) -> Dict[str, Any]:
        """Отключает API ключ"""
        return await self.update_user_key(key_hash, {"disabled": True})
    
    async def enable_user_key(self, key_hash: str) -> Dict[str, Any]:  # Исправлено: добавлено def
        """Включает API ключ"""
        return await self.update_user_key(key_hash, {"disabled": False})
    
    async def delete_user_key(self, key_hash: str) -> bool:
        """Удаляет API ключ"""
        try:
            await self._make_request("DELETE", key_hash)
            return True
        except Exception:
            return False
    
    async def get_key_usage(self, key_hash: str) -> Dict[str, float]:
        """Получает информацию об использовании ключа"""
        key_info = await self.get_user_key(key_hash)
        if key_info:
            return {
                "usage": key_info.get("usage", 0),
                "usage_daily": key_info.get("usage_daily", 0),
                "usage_weekly": key_info.get("usage_weekly", 0),
                "usage_monthly": key_info.get("usage_monthly", 0),
                "limit_remaining": key_info.get("limit_remaining", 0),
                "limit": key_info.get("limit", 0)
            }
        return {}