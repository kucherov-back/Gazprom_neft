# NOTES

## Что сделано
- Идемпотентная загрузка по `sha256` + `?force=true`; дедуп исключает статус `ERROR`.
- `GET /api/stats` - все агрегаты **одним SQL-запросом**, медиана через оконную функцию.
- Alembic (async, aiosqlite): миграции `archive_sha256` и `dedup_count`, up/down проверены.
- 3 слоя: `routers` (HTTP) / `services` (бизнес-логика) / `db.repositories` (данные).
- Конфиг через `pydantic-settings` (+ `.env.example`), логирование через `dictConfig`,
  глобальные exception-handlers.
- 16 тестов (in-memory sqlite, изоляция per-test), uv + ruff, Docker (multi-stage,
  non-root, миграции в entrypoint), CI на GitHub Actions (lint + format + tests + docker).

## Решения и допущения
- **Хэш**: считается из `await file.read()` целиком в память; перед обработкой проверяется
  лимит `MAX_UPLOAD_SIZE_MB` (по умолчанию 50) -> `413`. Для больших файлов в проде - потоковое
  чтение чанками в `hashlib.update()` с тем же лимитом.
- **Гонка** двух одинаковых архивов: `unique index` на `archive_sha256` + перехват
  `IntegrityError` -> `rollback` -> повторный дедуп существующей задачи.
- **force=true**: задача создаётся с `archive_sha256=NULL` (несколько NULL не конфликтуют с
  unique index). Следствие: force-задача не участвует в будущем дедупе - это осознанно.
- **ERROR-задачи**: перед созданием новой задачи их хэш очищается (`clear_hash_for_errored`),
  чтобы unique index не мешал переобработке упавшего архива.
- **Медиана**: sqlite не имеет встроенной функции. Считается `row_number()`/`count() over`
  с сортировкой по **реальной длительности** (`julianday(finished)-julianday(created)`), затем
  усреднением 1-2 центральных строк. Изначальная сортировка по строковой разнице дат давала
  константный ключ (год-год=0) и неверную медиану - исправлено, покрыто тестами odd/even.
- **Один запрос**: медиана вложена скалярным подзапросом в основной `SELECT` агрегатов.
- **Фоновая обработка**: `BackgroundTasks` (а не «висячий» `asyncio.create_task`); открывает
  собственную сессию, помечает задачу `DONE`/`finished_at`, при ошибке - `ERROR`. Так статистика
  времени обработки наполняется реально, а не остаётся `null`.
- **Happy-path** не сломан: первичная загрузка -> `{task_id, deduplicated:false}` + обработка.

## БД: sqlite vs PostgreSQL
По условию задания используется sqlite (локально, без инфраструктуры). Слои async-совместимы
с PostgreSQL без изменений модели; sqlite-специфична только медиана/`julianday` в статистике.
Для PG: `extract(epoch from finished_at - created_at)` + `percentile_cont(0.5) within group`.

## Что сделал бы дальше
- Потоковое хэширование чанками для больших архивов.
- Реальный воркер/очередь (Celery/arq) вместо `BackgroundTasks` для дорогой обработки.
- Прогон stats-тестов против Postgres (testcontainers), чтобы зелёный sqlite не давал ложную
  уверенность; partial unique index `WHERE status != 'ERROR'` вместо очистки хэша.

## Как проверял
- `uv run pytest` - 16/16 passed; `uv run ruff check .` / `ruff format --check .` - чисто.
- `alembic upgrade head` / `downgrade base` - обе стороны миграций.
- Медиана отдельно проверена на наборах odd/even/single/two/five.
- Локальный запуск uvicorn: загрузка, дедуп, force, stats на пустой и заполненной БД.
