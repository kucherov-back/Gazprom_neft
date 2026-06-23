"""
Заготовка EmbeddingMatcher — семантический матчер на эмбеддингах:
  - косинусная близость нормализованных значений requested/suggested;
  - модель — лёгкая локальная (sentence-transformers, мультиязычная) или embeddings-API;
  - КЭШ эмбеддингов (одинаковые строки не считаем дважды);
  - порог принятия решения — конфигурируемый, не хардкод.
"""
from app.core.interfaces import IAttributeMatcher
from app.core.schemas import RequestedAttribute, SuggestedAttribute, MatchResult


class EmbeddingMatcher(IAttributeMatcher):
    def __init__(self, matched_threshold: float = 0.75, partial_threshold: float = 0.55):
        self.matched_threshold = matched_threshold
        self.partial_threshold = partial_threshold
        # TODO(кандидат): инициализация модели эмбеддингов + кэш.

    def match(self, requested: RequestedAttribute, suggested: SuggestedAttribute) -> MatchResult:
        raise NotImplementedError("реализуй косинусную близость эмбеддингов + пороги")
