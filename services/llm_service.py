import litellm
from litellm import completion
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, model: str, api_key: str):
        self.model = model

        # --- Правильная конфигурация OpenRouter ---
        litellm.api_key = api_key              # обязательно
        litellm.openrouter_key = api_key       # обязательно
        litellm.use_client = "openrouter"      # критично
        # ------------------------------------------

    async def parse_transaction(self, text: str) -> Optional[Dict]:
        prompt = f"""
        Проанализируй текст и извлеки информацию о финансовой операции в JSON формате.

        Текст: "{text}"

        Извлеки:
        - type: "доход" или "расход"
        - amount: число
        - currency: валюта (по умолчанию RUB)
        - category
        - description
        - date (YYYY-MM-DD)

        Верни строго JSON.
        """

        try:
            response = await completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            content = response.choices[0].message.content

            # Извлекаем JSON
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]

            return json.loads(json_str)

        except Exception as e:
            logger.error(f"Error parsing transaction: {e}")
            return None
