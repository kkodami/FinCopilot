import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from config import config
from services.user_manager import UserManager

logger = logging.getLogger(__name__)

class OpenRouterService:
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self.user_manager = UserManager()
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_headers = {
            "HTTP-Referer": config.OPENROUTER_REFERER,
            "X-Title": config.OPENROUTER_TITLE,
            "Content-Type": "application/json"
        }
    
    async def _get_api_key(self) -> str:
        """Получает API ключ для пользователя"""
        if self.user_id:
            try:
                user = await self.user_manager.get_or_create_user(
                    self.user_id, 
                    "temp",  # Эти значения будут перезаписаны при реальном использовании
                    "User"
                )
                return user.openrouter_key or config.OPENROUTER_API_KEY
            except Exception as e:
                logger.error(f"Error getting user API key: {e}")
                return config.OPENROUTER_API_KEY
        return config.OPENROUTER_API_KEY
    
    async def _make_request(self, payload: dict) -> dict:
        """Выполняет запрос к OpenRouter API"""
        api_key = await self._get_api_key()
        
        headers = {**self.default_headers, "Authorization": f"Bearer {api_key}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 402:
                    raise Exception("Недостаточно средств на API ключе. Пожалуйста, пополните баланс или обратитесь к администратору.")
                elif response.status == 429:
                    raise Exception("Превышен лимит запросов. Попробуйте позже или используйте команду /usage для проверки лимитов.")
                elif response.status == 401:
                    raise Exception("Неверный API ключ. Пожалуйста, обратитесь к администратору.")
                else:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error {response.status}: {error_text}")
                    raise Exception(f"Ошибка API: {response.status}. Попробуйте еще раз.")
    
    async def parse_transaction(self, text: str) -> dict:
        """Парсит текст транзакции с помощью LLM"""
        
        prompt = f"""
        Ты финансовый ассистент. Проанализируй текст транзакции и верни JSON с полями:
        - type: "income" (доход) или "expense" (расход)
        - amount: число (сумма)
        - currency: валюта (RUB, USD, EUR - по умолчанию RUB)
        - category: категория из списка [маркетинг, зарплата, аренда, продукты, транспорт, оборудование, услуги, развлечения, налоги, прочее]
        - subcategory: уточняющая подкатегория или null
        - date: дата в формате YYYY-MM-DD (сегодня, если не указано)
        - description: краткое описание на русском

        Текст: "{text}"

        Важно: верни ТОЛЬКО JSON без каких-либо дополнительных текстовых объяснений.

        Примеры:
        Вход: "расход 2500 рублей на рекламу сегодня"
        Выход: {{"type": "expense", "amount": 2500, "currency": "RUB", "category": "маркетинг", "subcategory": "реклама", "date": "2024-01-15", "description": "Рекламная кампания"}}

        Вход: "доход 12000 за кофе вчера"
        Выход: {{"type": "income", "amount": 12000, "currency": "RUB", "category": "услуги", "subcategory": "кофе", "date": "2024-01-14", "description": "Продажа кофе"}}

        Вход: "трата 5000 обед с клиентом"
        Выход: {{"type": "expense", "amount": 5000, "currency": "RUB", "category": "прочее", "subcategory": "обед", "date": "2024-01-15", "description": "Обед с клиентом"}}

        Вход: "приход 30000 зарплата"
        Выход: {{"type": "income", "amount": 30000, "currency": "RUB", "category": "зарплата", "subcategory": null, "date": "2024-01-15", "description": "Зарплата"}}
        """
        
        payload = {
            "model": config.OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 500,
            "stream": False
        }
        
        try:
            response = await self._make_request(payload)
            
            # Извлекаем JSON из ответа
            content = response['choices'][0]['message']['content']
            
            # Очищаем ответ от возможных markdown форматирования
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            parsed_data = json.loads(content)
            
            # Валидация обязательных полей
            required_fields = ['type', 'amount', 'category']
            for field in required_fields:
                if field not in parsed_data:
                    raise Exception(f"Отсутствует обязательное поле: {field}")
            
            # Нормализация типа
            if parsed_data['type'] in ['доход', 'income', 'приход']:
                parsed_data['type'] = 'income'
            else:
                parsed_data['type'] = 'expense'
            
            # Нормализация валюты
            if 'currency' not in parsed_data:
                parsed_data['currency'] = 'RUB'
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}, content: {content}")
            raise Exception("Не удалось распознать формат транзакции. Пожалуйста, укажите данные в формате: 'расход 1000 на обед'")
        except Exception as e:
            logger.error(f"Error parsing transaction: {e}")
            raise e
    
    async def generate_report(self, data: dict, period: str) -> str:
        """Генерирует аналитический отчет на основе данных"""
        
        # Форматируем данные для лучшего восприятия LLM
        incomes_summary = ""
        expenses_summary = ""
        
        if data.get('incomes'):
            incomes_summary = "Доходы по категориям:\n" + "\n".join([
                f"- {cat}: {amount:.2f} руб" 
                for cat, amount in data.get('income_by_category', {}).items()
            ])
        
        if data.get('expenses'):
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
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 800,
            "stream": False
        }
        
        try:
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
            return (
                f"📊 Базовый отчет за {period}:\n\n"
                f"• 💰 Доходы: {data.get('total_income', 0):.2f} руб\n"
                f"• 💸 Расходы: {data.get('total_expense', 0):.2f} руб\n"
                f"• 📈 Прибыль: {data.get('profit', 0):.2f} руб\n"
                f"• 🔢 Операций: {data.get('transactions_count', 0)}\n\n"
                f"💡 Для детального анализа с AI-рекомендациями проверьте баланс API ключа командой /usage"
            )
    
    async def generate_insights(self, transactions: list) -> str:
        """Генерирует инсайты и рекомендации на основе транзакций"""
        
        if not transactions:
            return "📝 Пока недостаточно данных для анализа. Продолжайте записывать транзакции!"
        
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
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,
            "max_tokens": 500,
            "stream": False
        }
        
        try:
            response = await self._make_request(payload)
            return response['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return "💡 Аналитика временно недоступна. Продолжайте записывать транзакции для будущего анализа!"
    
    async def categorize_transaction(self, description: str, amount: float) -> str:
        """Автоматически определяет категорию для транзакции"""
        
        prompt = f"""
        Определи наиболее подходящую категорию для финансовой транзакции.
        
        Описание: "{description}"
        Сумма: {amount} руб
        
        Выбери категорию из списка: [маркетинг, зарплата, аренда, продукты, транспорт, оборудование, услуги, развлечения, налоги, прочее]
        
        Верни ТОЛЬКО название категории без дополнительных объяснений.
        """
        
        payload = {
            "model": config.OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 50,
            "stream": False
        }
        
        try:
            response = await self._make_request(payload)
            category = response['choices'][0]['message']['content'].strip()
            
            # Валидация категории
            valid_categories = ['маркетинг', 'зарплата', 'аренда', 'продукты', 'транспорт', 'оборудование', 'услуги', 'развлечения', 'налоги', 'прочее']
            if category not in valid_categories:
                return 'прочее'
            
            return category
            
        except Exception as e:
            logger.error(f"Error categorizing transaction: {e}")
            return 'прочее'
    
    async def check_health(self) -> bool:
        """Проверяет доступность OpenRouter API"""
        try:
            payload = {
                "model": config.OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5,
                "stream": False
            }
            
            await self._make_request(payload)
            return True
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            return False