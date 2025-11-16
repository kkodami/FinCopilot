from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    openrouter_key: Optional[str] = None
    key_hash: Optional[str] = None
    credit_limit: float = 100.0
    is_premium: bool = False
    created_at: str = None
    last_activity: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.last_activity is None:
            self.last_activity = datetime.now().isoformat()
    
    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return f"{self.first_name} {self.last_name or ''}".strip()