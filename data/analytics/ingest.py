"""
Скелет загрузчика логов.

Задача: распарсить построчный JSON из лог-директории, нормализовать в табличную
модель и загрузить в DuckDB/Postgres ИДЕМПОТЕНТНО.

Запуск:  python -m analytics.ingest sample_logs/
"""
import sys
from pathlib import Path


def iter_events(logs_dir: str):
    """Итерируется по событиям, устойчиво пропуская битые строки."""
    bad = 0
    total = 0
    for path in Path(logs_dir).glob("*.log"):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                # TODO(кандидат): json.loads с try/except; считать % брака.
                _ = line
    # TODO(кандидат): вернуть распарсенные события + метрику качества (bad/total).
    raise NotImplementedError


def main():
    logs_dir = sys.argv[1] if len(sys.argv) > 1 else "sample_logs/"
    # TODO(кандидат): нормализация в таблицу фактов + идемпотентная загрузка в DuckDB.
    raise NotImplementedError(f"реализуй ingest для {logs_dir}")


if __name__ == "__main__":
    main()
