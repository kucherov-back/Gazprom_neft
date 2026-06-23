"""Контракт стратегии сравнения атрибутов."""
from abc import ABC, abstractmethod

from app.core.schemas import RequestedAttribute, SuggestedAttribute, MatchResult


class IAttributeMatcher(ABC):
    @abstractmethod
    def match(self, requested: RequestedAttribute, suggested: SuggestedAttribute) -> MatchResult:
        """Сравнить требование и предложение, вернуть решение + score [0..1]."""
        ...
