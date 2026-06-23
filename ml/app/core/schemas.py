"""Схемы данных для сопоставления атрибутов."""
import enum
from pydantic import BaseModel


class MatchingDecision(str, enum.Enum):
    MATCHED = "matched"
    PARTIAL = "partial"
    MISMATCH = "mismatch"


class RequestedAttribute(BaseModel):
    code: str
    name: str
    value: str          # требование Заказчика, например "нержавеющая сталь"


class SuggestedAttribute(BaseModel):
    code: str
    value: str          # предложение Поставщика, например "сталь 12Х18Н10Т"


class MatchResult(BaseModel):
    decision: MatchingDecision
    score: float        # 0..1
    reasoning: str = ""
