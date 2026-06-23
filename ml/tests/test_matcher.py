"""Тест baseline; тесты на EmbeddingMatcher добавляешь рядом."""
from app.core.schemas import RequestedAttribute, SuggestedAttribute, MatchingDecision
from app.modules.fuzzy_matcher import FuzzyMatcher


def test_fuzzy_exact():
    m = FuzzyMatcher()
    req = RequestedAttribute(code="x", name="x", value="электропривод")
    sug = SuggestedAttribute(code="x", value="электропривод")
    assert m.match(req, sug).decision == MatchingDecision.MATCHED

# TODO(кандидат): тест EmbeddingMatcher — happy-path (синоним) + пограничный кейс.
