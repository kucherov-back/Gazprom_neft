# NOTES

## Что сделано
- Инициализирован Alembic с async-конфигурацией (aiosqlite)
- Создан pyproject.toml с фиксированными версиями зависимостей

## Решения и допущения
- `render_as_batch=True` в Alembic — необходим для корректной работы миграций с SQLite (ALTER TABLE ограничения)
- URL БД задан в alembic.ini: `sqlite+aiosqlite:///./stand.db`

## Что не успел / сделал бы дальше
- Часть 1: идемпотентная загрузка по sha256
- Часть 2: эндпоинт /api/stats

## Как проверял
- `python -m alembic current` — конфигурация работает без ошибок