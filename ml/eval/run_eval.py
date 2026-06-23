"""
Скелет offline-эвала.

Задача: расширить датасет до ≥20 кейсов (синонимы, единицы, шум), посчитать
precision/recall/F1 для fuzzy vs embedding vs (fuzzy→embedding fallback), вывести
таблицу и вывод — где какой подход выигрывает.

Запуск:  python -m eval.run_eval
"""
import json
from pathlib import Path

from app.core.schemas import RequestedAttribute, SuggestedAttribute
from app.modules.fuzzy_matcher import FuzzyMatcher


def load_dataset(path: str = "eval/dataset.jsonl"):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main():
    rows = load_dataset()
    fuzzy = FuzzyMatcher()
    for r in rows:
        req = RequestedAttribute(code="x", name="x", value=r["requested"])
        sug = SuggestedAttribute(code="x", value=r["suggested"])
        res = fuzzy.match(req, sug)
        print(f"[fuzzy] exp={r['expected']:9} got={res.decision.value:9} score={res.score:.2f}  "
              f"{r['requested']!r} ~ {r['suggested']!r}")

    # TODO(кандидат): метрики precision/recall/F1 (мульти-класс или matched-vs-rest),
    #   прогон EmbeddingMatcher, сравнительная таблица и выводы.


if __name__ == "__main__":
    main()
