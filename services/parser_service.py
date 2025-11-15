import re
import uuid
from datetime import datetime
from typing import Dict, Optional
from services.llm_service import LLMService

class TransactionParser:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        
        # Базовые паттерны для быстрого парсинга
        self.patterns = {
            'amount': r'(\d+[.,]?\d*)\s*(руб|р|₽|usd|\$)',
            'type': {
                'расход': ['расход', 'потратил', 'оплатил', 'покупка', 'затраты'],
                'доход': ['доход', 'заработал', 'получил', 'выручка', 'прибыль']
            }
        }

    async def parse_transaction(self, text: str) -> Optional[Dict]:
        """Основной метод парсинга транзакции"""
        
        # Сначала пробуем быстрый парсинг по паттернам
        quick_parse = self._quick_parse(text)
        if quick_parse:
            return await self._enhance_with_llm(text, quick_parse)
        
        # Если быстрый парсинг не сработал, используем LLM
        return await self.llm.parse_transaction(text)

    def _quick_parse(self, text: str) -> Optional[Dict]:
        """Быстрый парсинг по регулярным выражениям"""
        try:
            text_lower = text.lower()
            
            # Определяем тип операции
            operation_type = None
            for type_key, keywords in self.patterns['type'].items():
                if any(keyword in text_lower for keyword in keywords):
                    operation_type = type_key
                    break
            
            if not operation_type:
                return None

            # Ищем сумму
            amount_match = re.search(r'(\d+[.,]?\d*)', text)
            if not amount_match:
                return None
                
            amount = float(amount_match.group(1).replace(',', '.'))
            
            # Базовая структура
            return {
                'type': operation_type,
                'amount': amount,
                'currency': 'RUB',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'uuid': str(uuid.uuid4())[:8]
            }
            
        except Exception:
            return None

    async def _enhance_with_llm(self, text: str, base_data: Dict) -> Dict:
        """Улучшаем данные с помощью LLM"""
        try:
            enhanced = await self.llm.parse_transaction(text)
            if enhanced:
                # Сохраняем UUID из быстрого парсинга
                enhanced['uuid'] = base_data['uuid']
                return enhanced
        except Exception:
            pass
        
        return base_data