"""
Baseline fuzzy-матчер.

Текущий подход: посимвольная близость через rapidfuzz. Плохо ловит семантику:
"нержавеющая сталь" vs "коррозионностойкая сталь 12Х18Н10Т" — по символам далеко.
Это baseline, с которым сравнивается EmbeddingMatcher.
"""
from rapidfuzz import fuzz

from app.core.interfaces import IAttributeMatcher
from app.core.schemas import RequestedAttribute, SuggestedAttribute, MatchResult, MatchingDecision


def normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


class FuzzyMatcher(IAttributeMatcher):
    def __init__(self, matched_threshold: float = 0.85, partial_threshold: float = 0.6):
        self.matched_threshold = matched_threshold
        self.partial_threshold = partial_threshold

    def match(self, requested: RequestedAttribute, suggested: SuggestedAttribute) -> MatchResult:
        score = fuzz.token_sort_ratio(normalize(requested.value), normalize(suggested.value)) / 100.0
        if score >= self.matched_threshold:
            decision = MatchingDecision.MATCHED
        elif score >= self.partial_threshold:
            decision = MatchingDecision.PARTIAL
        else:
            decision = MatchingDecision.MISMATCH
        return MatchResult(decision=decision, score=score, reasoning="rapidfuzz token_sort_ratio")
