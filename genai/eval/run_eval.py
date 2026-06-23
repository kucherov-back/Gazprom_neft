"""
Скелет мини-эвала.

Задача: расширить датасет (OCR-шум, противоречивые числа, отсутствие значения),
сравнить baseline vs grounded по accuracy извлечения и доле ГАЛЛЮЦИНАЦИЙ
(value, которого нет в тексте).

Запуск:  python -m eval.run_eval
"""
import json
import asyncio
from pathlib import Path

from app.modules.extractor import extract_attribute_baseline


def load():
    return [json.loads(l) for l in Path("eval/dataset.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


async def main():
    rows = load()
    for r in rows:
        res = await extract_attribute_baseline(r["text"], r["attr"])
        hallucinated = bool(res.value) and (res.source_quote or "") not in r["text"]
        print(f"exp={str(r['expected']):28} got={str(res.value):8} "
              f"hallucinated={hallucinated}  quote={res.source_quote!r}")

    # TODO(кандидат): accuracy + доля галлюцинаций для baseline vs grounded; таблица + вывод.


if __name__ == "__main__":
    asyncio.run(main())
