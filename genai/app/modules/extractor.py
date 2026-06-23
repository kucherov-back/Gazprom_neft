"""
Baseline-извлекатель атрибута + заготовка улучшенного.

Baseline: «текст → JSON», парсинг best-effort, БЕЗ грунтинга и без проверки уверенности.
Задача — extract_attribute_grounded: structured output + few-shot + грунтинг-фильтр
(source_quote обязан присутствовать в тексте, иначе value=None).
"""
import re
import json

from pydantic import BaseModel

from app.modules.registry import AttributeDefinition, get_attribute
from app.utils.llm_client import LLMClient


class ExtractedValue(BaseModel):
    value: str | None = None
    unit: str | None = None
    confidence: str | None = None       # high | medium | low
    source_quote: str | None = None
    rejected_reason: str | None = None  # почему отбраковано (для грунтинг-фильтра)


def _loose_json(raw: str) -> dict | None:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


async def extract_attribute_baseline(text: str, attr_code: str) -> ExtractedValue:
    """Текущий подход — доверяем модели как есть."""
    attr = get_attribute(attr_code)
    llm = LLMClient()
    raw = await llm.complete(
        system="Извлеки значение атрибута. Верни JSON: value, unit, confidence, source_quote.",
        user=f"Атрибут: {attr.display_name}\nТекст: {text}",
    )
    data = _loose_json(raw) or {}
    return ExtractedValue(**{k: data.get(k) for k in ("value", "unit", "confidence", "source_quote")})


async def extract_attribute_grounded(text: str, attr_code: str) -> ExtractedValue:
    """
    TODO(кандидат):
      - few-shot промпт (вынести в app/prompts/), structured output;
      - устойчивый парсинг + осмысленный retry;
      - ГРУНТИНГ: если source_quote отсутствует в тексте — value=None + rejected_reason.
    """
    raise NotImplementedError
