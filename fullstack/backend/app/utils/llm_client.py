"""
LLM-клиент: async-вызов chat-completions, возвращает строку.

Чтобы UI можно было разрабатывать без живого ключа, клиент работает в двух режимах:
  - LLM_FAKE=1 (по умолчанию) — возвращает фиксированный правдоподобный ответ;
  - иначе — можно подключить OpenAI-совместимый endpoint.
"""
import os
import asyncio
import json


class LLMClient:
    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self.api_url = api_url or os.getenv("LLM_API_URL", "")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.fake = os.getenv("LLM_FAKE", "1") == "1"

    async def complete(self, system: str, user: str) -> str:
        """Возвращает сырой текстовый ответ модели."""
        if self.fake:
            await asyncio.sleep(0.05)
            # Намеренно завёрнуто в markdown — кандидат должен это вычистить.
            return "```json\n" + json.dumps({
                "pattern": r"\bD[NY]\s*([0-9]+)\b",
                "flags": "IGNORECASE",
                "explanation": "Ищем DN/DY с числом, захватываем число группой.",
            }, ensure_ascii=False) + "\n```"
        raise NotImplementedError(
            "Реальный вызов LLM не настроен. Поднимай через LLM_FAKE=1 или подключи endpoint."
        )
