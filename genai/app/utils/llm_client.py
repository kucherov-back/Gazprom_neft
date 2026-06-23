"""
LLM-клиент поверх OpenAI-совместимого chat-completions.

С LLM_FAKE=1 (по умолчанию) возвращает правдоподобные ответы — иногда с
галлюцинацией (значение, которого нет в тексте), чтобы грунтинг-фильтр было на чём
проверить, и можно было работать без живого ключа.
"""
import os
import re
import json
import random
import asyncio


class LLMClient:
    def __init__(self):
        self.fake = os.getenv("LLM_FAKE", "1") == "1"

    async def complete(self, system: str, user: str) -> str:
        if self.fake:
            await asyncio.sleep(0.05)
            # Пытаемся «извлечь» число из user-текста; в 25% случаев галлюцинируем.
            m = re.search(r"(\d+(?:[.,]\d+)?)", user)
            if m and random.random() > 0.25:
                value = m.group(1)
                quote = user[max(0, m.start() - 10): m.end() + 10].strip()
            else:
                value = "999"            # значения нет в тексте (галлюцинация)
                quote = "значение из справочника"  # цитаты в тексте нет
            return "```json\n" + json.dumps({
                "value": value, "unit": "мм", "confidence": "high", "source_quote": quote
            }, ensure_ascii=False) + "\n```"
        raise NotImplementedError("Подключи endpoint или используй LLM_FAKE=1")
