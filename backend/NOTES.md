# NOTES

## Что сделано
- Инициализирован Alembic с async-конфигурацией (aiosqlite)
- Создан pyproject.toml с фиксированными версиями зависимостей
- Добавлено поле `archive_sha256` в модель Task + Alembic-миграция
- Реализована идемпотентная загрузка: дедупликация по sha256, параметр `?force=true`
- Добавлено поле `dedup_count` в модель Task + миграция
- Реализован `GET /api/stats` — агрегаты одним SQL-запросом

## Решения и допущения
- `render_as_batch=True` в Alembic — для корректной работы миграций с SQLite
- Unique index на `archive_sha256` — защита от race condition
- Хэш считается от всего содержимого в памяти (файл уже целиком читается в `content`)
- `force=true` — задача создаётся с `archive_sha256=None`
- `dedup_count` на Task — атомарный инкремент через SQL UPDATE при каждой дедупликации
- Медиана в SQLite — через ROW_NUMBER() + AVG двух средних значений
- Время обработки считается как `julianday(finished_at) - julianday(created_at)` в секундах

## Что не успел / сделал бы дальше
- Тесты на дедуп, force, stats
- Потоковое хэширование для больших файлов

## Как проверял
- Ручной тест: загрузка, дедуп, force, разные файлы
- Проверка `/api/stats`: пустая БД, после загрузок с дедуп
- `python -m alembic upgrade head` / `downgrade base`