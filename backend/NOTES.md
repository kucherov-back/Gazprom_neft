# NOTES

## Что сделано
- Alembic (async, aiosqlite), две миграции: `archive_sha256` и `dedup_count`
- pyproject.toml с фиксированными версиями зависимостей
- Идемпотентная загрузка по sha256 с параметром `?force=true`
- `GET /api/stats` — агрегаты одним SQL-запросом, Pydantic-ответ
- 9 тестов с изоляцией через in-memory SQLite
- Dockerfile + docker-compose.yml

## Решения и допущения
- **Хэш**: считается целиком в памяти — файл уже читается через `await file.read()`. Для больших файлов нужно потоковое чтение чанками с лимитом размера.
- **Race condition**: unique index на `archive_sha256` + перехват `IntegrityError` с fallback на поиск существующей задачи.
- **force=true**: задача создаётся с `archive_sha256=None`, не конфликтует с unique constraint.
- **ERROR-задачи**: перед созданием новой задачи хэш у ERROR-задач с таким же sha256 очищается (`clear_hash_for_errored`).
- **dedup_count**: атомарный `UPDATE SET dedup_count = dedup_count + 1` — считает сколько раз загрузка была дедуплицирована.
- **Медиана**: SQLite не имеет встроенной функции — реализована через `ROW_NUMBER()` + `AVG` двух средних.
- **render_as_batch**: необходим для ALTER TABLE в SQLite.
- **Happy-path**: не сломан — первичная загрузка работает как раньше, возвращает `{task_id, deduplicated: false}`.

## Что не успел / сделал бы дальше
- Потоковое хэширование с лимитом размера файла
- CI/CD (GitHub Actions: lint + тесты)
- Перевод на Poetry

## Как проверял
- `python -m pytest tests/ -v` — 9/9 passed
- `python -m alembic upgrade head` / `downgrade base`
- Ручные скрипты: загрузка, дедуп, force, stats на пустой и заполненной БД
- `docker build` — Docker Desktop не установлен, синтаксис проверен