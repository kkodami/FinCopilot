from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware

class DependencyMiddleware(BaseMiddleware):
    def __init__(self, sheets_service, llm_service):
        super().__init__()
        self.sheets = sheets_service
        self.llm = llm_service

    async def __call__(self, handler: Callable, event, data: Dict[str, Any]) -> Awaitable:
        data["sheets_service"] = self.sheets
        data["llm_service"] = self.llm
        return await handler(event, data)
