import litellm
from litellm import completion
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, model: str = "gpt-3.5-turbo", api_key: str = None):
        self.model = model
        if api_key:
            litellm.openai_key = api_key

    async def parse_transaction(self, text: str) -> Optional[Dict]:
        """Парсинг транзакции из естественного языка"""
        prompt = f"""
        Проанализируй текст и извлеки информацию о финансовой операции в JSON формате.
        
        Текст: "{text}"
        
        Извлеки:
        - type: "доход" или "расход"
        - amount: число (сумма)
        - currency: валюта (по умолчанию "RUB")
        - category: категория (например, "реклама", "услуги", "товары")
        - description: описание операции
        - date: дата в формате YYYY-MM-DD (если указана, иначе сегодня)
        
        Пример ответа:
        {{
            "type": "расход",
            "amount": 2500,
            "currency": "RUB",
            "category": "реклама",
            "description": "контекстная реклама",
            "date": "2024-01-15"
        }}
        """
        
        try:
            response = await completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            # Извлекаем JSON из ответа
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_str = content[start_idx:end_idx]
            
            data = json.loads(json_str)
            return data
            
        except Exception as e:
            logger.error(f"Error parsing transaction: {e}")
            return None

    async def analyze_financial_data(self, data: Dict, analysis_type: str) -> str:
        """Анализ финансовых данных с помощью LLM"""
        
        if analysis_type == "monthly_report":
            prompt = f"""
            Проанализируй финансовые данные и предоставь краткий, но информативный отчет для предпринимателя.
            
            Данные:
            - Доходы: {data.get('income', 0)} руб
            - Расходы: {data.get('expenses', 0)} руб  
            - Прибыль: {data.get('profit', 0)} руб
            - Доходы по категориям: {data.get('income_by_category', {})}
            - Расходы по категориям: {data.get('expenses_by_category', {})}
            
            Сделай выводы:
            1. Общая финансовая ситуация
            2. Основные статьи доходов/расходов
            3. Рекомендации по оптимизации
            4. Потенциальные проблемы
            
            Будь конкретен и дай практические советы.
            """
        
        elif analysis_type == "profit_analysis":
            prompt = f"""
            Проанализируй прибыль бизнеса:
            
            Доход: {data.get('income', 0)} руб
            Расходы: {data.get('expenses', 0)} руб
            Прибыль: {data.get('profit', 0)} руб
            Рентабельность: {data.get('profit_margin', 0):.1f}%
            
            Дай рекомендации по увеличению прибыли.
            """
        
        else:
            prompt = f"""
            Проанализируй данные: {data}
            Сделай выводы и дай рекомендации для предпринимателя.
            """
        
        try:
            response = await completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in financial analysis: {e}")
            return "Не удалось проанализировать данные."

    async def extract_period_from_text(self, text: str) -> str:
        """Извлечение периода из текста запроса"""
        prompt = f"""
        Определи временной период из текста: "{text}"
        
        Возможные варианты: week, month, quarter, year
        
        Верни только одно слово - период.
        """
        
        try:
            response = await completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip().lower()
            
        except Exception as e:
            logger.error(f"Error extracting period: {e}")
            return "month"