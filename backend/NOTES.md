# NOTES

## Что сделано
- Инициализирован Alembic с async-конфигурацией (aiosqlite)
- Создан pyproject.toml с фиксированными версиями зависимостей
- Добавлено поле `archive_sha256` в модель Task + Alembic-миграция
- Реализована идемпотентная загрузка: дедупликация по sha256, параметр `?force=true`
- Добавлено поле `dedup_count` в модель Task + миграция
- Реализован `GET /api/stats` — агрегаты одним SQL-запросом
- 9 тестов: дедуп, force, upload после ERROR, stats (пустая БД, счётчики, время обработки)

## Решения и допущения
- `render_as_batch=True` в Alembic — для корректной работы миграций с SQLite
- Unique index на `archive_sha256` — защита от race condition
- Хэш считается от всего содержимого в памяти (файл уже целиком читается в `content`)
- `force=true` — задача создаётся с `archive_sha256=None`
- `dedup_count` на Task — атомарный инкремент через SQL UPDATE
- Медиана в SQLite — через ROW_NUMBER() + AVG двух средних значений
- Тесты используют in-memory SQLite с dependency override для изоляции

## Что не успел / сделал бы дальше
- Потоковое хэширование для больших файлов
- Docker, CI/CD, Poetry

## Как проверял
- `python -m pytest tests/ -v` — 9/9 passed
- Ручная проверка через скрипты: загрузка, дедуп, force, stats