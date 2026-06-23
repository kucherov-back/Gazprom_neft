# NOTES

## Что сделано
- Инициализирован Alembic с async-конфигурацией (aiosqlite)
- Создан pyproject.toml с фиксированными версиями зависимостей
- Добавлено поле `archive_sha256` в модель Task + Alembic-миграция
- Реализована идемпотентная загрузка: дедупликация по sha256, параметр `?force=true`
- Pydantic-схема `UploadResponse` для ответа

## Решения и допущения
- `render_as_batch=True` в Alembic — для корректной работы миграций с SQLite
- Unique index на `archive_sha256` — защита от race condition при параллельных загрузках
- Хэш считается от всего содержимого в памяти (файл уже целиком читается в `content`)
- `force=true` — задача создаётся с `archive_sha256=None`, не конфликтует с unique constraint
- При IntegrityError (race condition) — rollback + поиск существующей задачи
- ERROR-задачи: перед созданием новой очищаем хэш у задач в статусе ERROR с таким же sha256

## Что не успел / сделал бы дальше
- Часть 2: эндпоинт /api/stats
- Тесты на дедуп и stats

## Как проверял
- Ручной тест: 4 сценария (новый файл, дедуп, force, другой файл) — все прошли
- `python -m alembic upgrade head` / `downgrade base`