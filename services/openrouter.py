import aiohttp
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any
from config import config

logger = logging.getLogger(__name__)

class OpenRouterService:
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "HTTP-Referer": config.OPENROUTER_REFERER,
            "X-Title": config.OPENROUTER_TITLE,
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, payload: dict) -> dict:
        """Выполняет запрос к OpenRouter API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error {response.status}: {error_text}")
                        raise Exception(f"Ошибка API: {response.status}")
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise Exception("Сервис временно недоступен")
    
    async def parse_transaction(self, text: str) -> Dict[str, Any]:
        """Парсит текст транзакции"""
        try:
            # Сначала пробуем AI парсинг
            return await self._parse_with_ai(text)
        except Exception as e:
            logger.warning(f"AI parsing failed, using fallback: {e}")
            # Fallback на простой парсинг
            return self._simple_parse(text)
    
    async def _parse_with_ai(self, text: str) -> Dict[str, Any]:
        """Парсинг с помощью AI"""
        prompt = f"""Проанализируй текст транзакции и верни JSON. Текст: "{text}"
        
        Поля: 
        - type: "income" или "expense"
        - amount: число
        - currency: "RUB", "USD", "EUR" (по умолчанию "RUB")
        - category: маркетинг, зарплата, аренда, продукты, транспорт, оборудование, услуги, развлечения, налоги, прочее
        - subcategory: строка или null
        - date: YYYY-MM-DD (сегодня если не указано)
        - description: краткое описание
        
        Верни ТОЛЬКО JSON без других текстов."""
        
        payload = {
            "model": config.OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        response = await self._make_request(payload)
        content = response['choices'][0]['message']['content'].strip()
        
        # Очистка ответа
        content = content.replace('```json', '').replace('```', '').strip()
        
        parsed_data = json.loads(content)
        
        # Нормализация
        if parsed_data['type'] in ['доход', 'income', 'приход']:
            parsed_data['type'] = 'income'
        else:
            parsed_data['type'] = 'expense'
        
        parsed_data['currency'] = parsed_data.get('currency', 'RUB')
        parsed_data['date'] = parsed_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        return parsed_data
    
    def _simple_parse(self, text: str) -> Dict[str, Any]:
        """Простой парсинг без AI"""
        text_lower = text.lower()
        
        # Тип транзакции
        if any(word in text_lower for word in ['доход', 'приход']):
            trans_type = 'income'
        else:
            trans_type = 'expense'
        
        # Сумма
        amount = 0
        amount_match = re.search(r'(\d+[.,]?\d*)', text)
        if amount_match:
            try:
                amount = float(amount_match.group(1).replace(',', '.'))
            except:
                pass
        
        # Категория
        category_keywords = {
            'маркетинг': ['реклама', 'маркетинг', 'продвижение'],
            'зарплата': ['зарплата', 'оклад'],
            'аренда': ['аренда', 'аренд', 'съем'],
            'продукты': ['продукты', 'еда', 'супермаркет', 'магазин'],
            'транспорт': ['транспорт', 'бензин', 'такси', 'метро'],
            'оборудование': ['оборудование', 'техника', 'компьютер'],
            'услуги': ['услуги', 'сервис', 'подписка'],
            'развлечения': ['развлечения', 'кино', 'ресторан', 'кафе'],
            'налоги': ['налоги', 'налог']
        }
        
        category = 'прочее'
        for cat, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                category = cat
                break
        
        return {
            'type': trans_type,
            'amount': amount,
            'currency': 'RUB',
            'category': category,
            'subcategory': None,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'description': text[:50]
        }
    
    async def generate_report(self, data: dict, period: str) -> str:
        """Генерирует аналитический отчет на основе данных"""
        try:
            # Форматируем данные для промпта
            incomes_summary = ""
            expenses_summary = ""
            
            if data.get('income_by_category'):
                incomes_summary = "Доходы по категориям:\n" + "\n".join([
                    f"- {cat}: {amount:.2f} руб" 
                    for cat, amount in data.get('income_by_category', {}).items()
                ])
            
            if data.get('expense_by_category'):
                expenses_summary = "Расходы по категориям:\n" + "\n".join([
                    f"- {cat}: {amount:.2f} руб" 
                    for cat, amount in data.get('expense_by_category', {}).items()
                ])
            
            prompt = f"""
            Ты финансовый аналитик. На основе данных сгенерируй краткий, но информативный отчет на русском.
            
            Период: {period}
            
            Основные показатели:
            - Общий доход: {data.get('total_income', 0):.2f} руб
            - Общий расход: {data.get('total_expense', 0):.2f} руб  
            - Прибыль: {data.get('profit', 0):.2f} руб
            - Количество операций: {data.get('transactions_count', 0)}
            
            {incomes_summary}
            
            {expenses_summary}
            
            Проанализируй и предоставь:
            1. Общую финансовую картину (положительная/отрицательная динамика)
            2. Основные статьи доходов и расходов
            3. 1-2 конкретные рекомендации по оптимизации
            4. Выдели важные тенденции или аномалии если есть

            Будь профессиональным, но дружелюбным. Используй смайлики где уместно.
            Максимум 250 слов. Структурируй ответ с помощью эмодзи.
            """
            
            payload = {
                "model": config.OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 800
            }
            
            response = await self._make_request(payload)
            report = response['choices'][0]['message']['content']
            
            # Добавляем базовую статистику в начало отчета
            basic_stats = (
                f"📊 Финансовый отчет за {period}:\n\n"
                f"• 💰 Доходы: {data.get('total_income', 0):.2f} руб\n"
                f"• 💸 Расходы: {data.get('total_expense', 0):.2f} руб\n"
                f"• 📈 Прибыль: {data.get('profit', 0):.2f} руб\n"
                f"• 🔢 Операций: {data.get('transactions_count', 0)}\n\n"
            )
            
            return basic_stats + report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            # Fallback отчет без AI
            return self._generate_basic_report(data, period)
    
    def _generate_basic_report(self, data: dict, period: str) -> str:
        """Генерирует базовый отчет без AI"""
        profit = data.get('profit', 0)
        profit_emoji = "📈" if profit > 0 else "📉" if profit < 0 else "➡️"
        
        return (
            f"📊 Базовый отчет за {period}:\n\n"
            f"• 💰 Доходы: {data.get('total_income', 0):.2f} руб\n"
            f"• 💸 Расходы: {data.get('total_expense', 0):.2f} руб\n"
            f"• {profit_emoji} Прибыль: {profit:.2f} руб\n"
            f"• 🔢 Операций: {data.get('transactions_count', 0)}\n\n"
            f"💡 Для детального анализа с AI-рекомендациями проверьте настройки API"
        )
    
    async def generate_insights(self, transactions: list) -> str:
        """Генерирует инсайты и рекомендации на основе транзакций"""
        if not transactions:
            return "📝 Пока недостаточно данных для анализа. Продолжайте записывать транзакции!"
        
        try:
            # Группируем транзакции по категориям
            expenses_by_category = {}
            incomes_by_category = {}
            
            for t in transactions[-20:]:  # Берем последние 20 транзакций
                category = t.get('category', 'прочее')
                amount = t.get('amount', 0)
                
                if t.get('type') == 'expense':
                    expenses_by_category[category] = expenses_by_category.get(category, 0) + amount
                else:
                    incomes_by_category[category] = incomes_by_category.get(category, 0) + amount
            
            # Форматируем для промпта
            expenses_summary = "\n".join([
                f"- {cat}: {amount:.2f} руб" 
                for cat, amount in sorted(expenses_by_category.items(), key=lambda x: x[1], reverse=True)[:5]
            ]) if expenses_by_category else "Нет данных о расходах"
            
            incomes_summary = "\n".join([
                f"- {cat}: {amount:.2f} руб" 
                for cat, amount in sorted(incomes_by_category.items(), key=lambda x: x[1], reverse=True)[:5]
            ]) if incomes_by_category else "Нет данных о доходах"
            
            prompt = f"""
            Проанализируй финансовые данные и дай 3 кратких, практичных совета для предпринимателя:
            
            Основные статьи доходов:
            {incomes_summary}
            
            Основные статьи расходов:
            {expenses_summary}
            
            Дай конкретные рекомендации:
            1. По оптимизации расходов (какую категорию стоит сократить и почему)
            2. По увеличению доходов (на основе текущей структуры)
            3. Общий финансовый совет для улучшения ситуации
            
            Будь конкретным, практичным и кратким. Ответь на русском, используй деловой стиль со смайликами.
            Максимум 150 слов.
            """
            
            payload = {
                "model": config.OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 500
            }
            
            response = await self._make_request(payload)
            return response['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return "💡 Аналитика временно недоступна. Продолжайте записывать транзакции для будущего анализа!"