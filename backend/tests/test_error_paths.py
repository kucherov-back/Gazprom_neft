import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import engine as engine_module
from app.db.models import Task, TaskStatus
from app.main import app
from app.services import task_service
from app.services.task_service import TaskService, process_task
from tests.conftest import session_factory


def _zip(content: bytes = b"data"):
    return {"file": ("a.zip", content, "application/zip")}


class _RacingRepo:
    """Имитирует гонку: дедуп пуст, create падает IntegrityError, после rollback
    существующая задача находится (или нет, если existing=None)."""

    def __init__(self, existing_after_conflict: Task | None):
        self._existing = existing_after_conflict
        self._dedup_calls = 0

    async def get_active_by_hash(self, archive_sha256: str) -> Task | None:
        self._dedup_calls += 1
        return None if self._dedup_calls == 1 else self._existing

    async def clear_hash_for_errored(self, archive_sha256: str) -> None: ...

    async def create(self, task: Task) -> Task:
        raise IntegrityError("INSERT", {}, Exception("UNIQUE"))

    async def rollback(self) -> None: ...

    async def increment_dedup_count(self, task_id: str) -> None: ...


async def test_classify_zip_resolves_integrity_race():
    existing = Task(id="winner", original_filename="a.zip", status=TaskStatus.PROCESSING)
    service = TaskService(_RacingRepo(existing))

    response, should_process = await service.classify_zip(
        content=b"x", filename="a.zip", force=False
    )
    assert response.deduplicated is True
    assert response.task_id == "winner"
    assert should_process is False


async def test_classify_zip_reraises_when_race_unresolved():
    service = TaskService(_RacingRepo(None))
    with pytest.raises(IntegrityError):
        await service.classify_zip(content=b"x", filename="a.zip", force=False)


async def test_integrity_error_returns_409(client, monkeypatch):
    async def boom(self, **kwargs):
        raise IntegrityError("INSERT", {}, Exception("UNIQUE"))

    monkeypatch.setattr(TaskService, "classify_zip", boom)
    r = await client.post("/api/classify-zip/", files=_zip())
    assert r.status_code == 409
    assert r.json() == {"detail": "Resource conflict"}


async def test_unhandled_error_returns_500(monkeypatch):
    async def boom(self):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(TaskService, "get_stats", boom)
    # raise_app_exceptions=False: транспорт не пробрасывает ошибку, отдаёт ответ 500.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/stats")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error"}


async def test_process_task_marks_error_on_failure(monkeypatch):
    async with session_factory() as session:
        session.add(Task(id="t1", original_filename="f", status=TaskStatus.PROCESSING))
        await session.commit()

    def boom():
        raise RuntimeError("processing crashed")

    monkeypatch.setattr(task_service, "utcnow", boom)
    await process_task("t1")

    async with session_factory() as session:
        task = await session.get(Task, "t1")
    assert task.status == TaskStatus.ERROR


async def test_init_db_creates_schema(monkeypatch):
    eng = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(engine_module, "engine", eng)
    await engine_module.init_db()

    async with eng.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = result.scalars().all()
    await eng.dispose()
    assert "tasks" in tables
