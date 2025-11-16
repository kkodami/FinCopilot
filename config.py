import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Основные настройки
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    GOOGLE_SHEETS_CREDENTIALS: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID")
    
    # Настройки OpenRouter - используем бесплатную модель
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemma-7b-it:free")
    OPENROUTER_REFERER: str = os.getenv("OPENROUTER_REFERER", "https://github.com/fincopilot-bot")
    OPENROUTER_TITLE: str = os.getenv("OPENROUTER_TITLE", "FinCopilot")
    
    # Настройки пользователей
    DEFAULT_CREDIT_LIMIT: float = float(os.getenv("DEFAULT_CREDIT_LIMIT", "100"))
    PREMIUM_CREDIT_LIMIT: float = float(os.getenv("PREMIUM_CREDIT_LIMIT", "1000"))

config = Config()