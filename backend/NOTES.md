# NOTES

## Что сделано
- Инициализирован Alembic с async-конфигурацией (aiosqlite)
- Создан pyproject.toml с фиксированными версиями зависимостей
- Добавлено поле `archive_sha256` в модель Task (String(64), nullable, unique index)
- Создана Alembic-миграция с upgrade/downgrade

## Решения и допущения
- `render_as_batch=True` в Alembic — необходим для корректной работы миграций с SQLite
- `archive_sha256` — unique index для защиты от race condition при параллельных загрузках одинаковых файлов
- Поле nullable, т.к. существующие задачи могут не иметь хэша

## Что не успел / сделал бы дальше
- Часть 1: логика дедупликации в роутере и репозитории
- Часть 2: эндпоинт /api/stats

## Как проверял
- `python -m alembic upgrade head` / `downgrade base` — миграция применяется и откатывается