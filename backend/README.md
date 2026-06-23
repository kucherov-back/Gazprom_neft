# Document Processing - Backend

Сервис обработки документов: загрузка ZIP-архива создаёт `Task` и запускает фоновую
обработку (в продакшене - дорогие LLM/OCR-вызовы). Две ключевые возможности:

- **Идемпотентная загрузка** по `sha256`: повторная отправка того же архива не плодит
  задачи и не запускает обработку повторно (`?force=true` обходит дедуп).
- **Сводная статистика** `GET /api/stats` - агрегаты одним SQL-запросом (в БД, не в Python):
  количество по статусам, среднее/медианное время обработки, число дедупликаций.

## Стек

| Слой | Технологии |
|------|-----------|
| API | FastAPI 0.116, Uvicorn (ASGI) |
| Данные | SQLAlchemy 2.0 (async), aiosqlite, Alembic |
| Валидация/конфиг | Pydantic v2, pydantic-settings |
| Тесты/линт | pytest + pytest-asyncio, httpx, ruff |
| Тулинг/деплой | uv, Docker (multi-stage), GitHub Actions |

> БД - sqlite (по условию задания, локально без внешней инфраструктуры). Слои
> async-совместимы с PostgreSQL; sqlite-специфична только медиана в статистике
> (`julianday`), для PG её заменяет `percentile_cont` (см. [NOTES.md](NOTES.md)).

## Быстрый старт

```bash
# Docker - одной командой
docker compose up --build        # http://127.0.0.1:8000/docs

# Локально через uv
uv sync
cp .env.example .env              # при необходимости поправить
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Переменные окружения

Конфиг через `pydantic-settings` (env + `.env`). Шаблон - [.env.example](.env.example).

| Переменная | По умолчанию | Назначение |
|-----------|--------------|-----------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./stand.db` | Async DSN |
| `MAX_UPLOAD_SIZE_MB` | `50` | Лимит размера архива |
| `PROCESSING_DELAY_SECONDS` | `0.1` | Имитация длительности обработки |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `DEBUG` | `false` | Echo SQL и подробные ошибки |

## API

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/classify-zip/?force=false` | Загрузка ZIP -> `{task_id, deduplicated}` |
| `GET` | `/api/stats` | Агрегированная статистика по задачам |
| `GET` | `/health` | Healthcheck |

```bash
# Первая загрузка -> новая задача
curl -F "file=@archive.zip" http://127.0.0.1:8000/api/classify-zip/
# {"task_id":"...","deduplicated":false}

# Повтор того же файла -> та же задача, без обработки
curl -F "file=@archive.zip" http://127.0.0.1:8000/api/classify-zip/
# {"task_id":"<тот же>","deduplicated":true}

# Принудительно новая задача
curl -F "file=@archive.zip" "http://127.0.0.1:8000/api/classify-zip/?force=true"

curl http://127.0.0.1:8000/api/stats
# {"total":2,"by_status":{...},"avg_processing_seconds":0.1,
#  "median_processing_seconds":0.1,"deduplicated_count":1}
```

## Архитектура

Три слоя с чёткой ответственностью:

```
routers/   HTTP: валидация ввода, маппинг в ответ, фоновые задачи
services/  бизнес-логика: дедуп, force, разрешение гонок, оркестрация
db/        repositories - доступ к данным; models - ORM; engine - сессии
```

- Сессия создаётся на запрос через `Depends(get_session)` (пул на уровне движка).
- Гонка одинаковых архивов: `unique index` + перехват `IntegrityError` -> повторный дедуп.
- Глобальные exception-handlers вместо `try/except` в каждом эндпоинте.

## Тесты и линт

```bash
uv run pytest                                   # 22 теста: дедуп, force, гонка, медиана
uv run pytest --cov --cov-report=term-missing   # покрытие ~98% (gate в CI: 90%)
uv run ruff check .                             # линт (PEP 604, isort, bugbear, simplify)
uv run ruff format .                            # форматирование
```

## Миграции

```bash
uv run alembic upgrade head        # накатить
uv run alembic downgrade base      # откатить
uv run alembic revision --autogenerate -m "msg"
```
