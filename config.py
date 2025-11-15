import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Google Sheets
    GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    
    # LLM
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # OpenRouter (альтернатива)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")