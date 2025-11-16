from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

@dataclass
class Transaction:
    uuid: str
    date: str
    type: str  # "income" или "expense"
    category: str
    subcategory: Optional[str]
    amount: float
    currency: str
    description: str
    source: str
    created_at: str
    
    @classmethod
    def create_from_text(cls, text: str, parsed_data: dict):
        """Создает транзакцию из распознанного текста"""
        return cls(
            uuid=str(uuid.uuid4()),
            date=parsed_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            type=parsed_data['type'],
            category=parsed_data['category'],
            subcategory=parsed_data.get('subcategory'),
            amount=parsed_data['amount'],
            currency=parsed_data.get('currency', 'RUB'),
            description=parsed_data.get('description', ''),
            source=parsed_data.get('source', 'telegram'),
            created_at=datetime.now().isoformat()
        )