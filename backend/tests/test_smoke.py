import io
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.config import settings
from app.db.models import Task, TaskStatus
from tests.conftest import session_factory


def _zip_file(content: bytes = b"hello", name: str = "a.zip"):
    return {"file": (name, io.BytesIO(content), "application/zip")}


async def _mark_done(task_id: str, *, seconds: float) -> None:
    """Помечаем задачу DONE с заданной длительностью обработки."""
    now = datetime.now(UTC)
    async with session_factory() as session:
        await session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(
                status=TaskStatus.DONE,
                created_at=now - timedelta(seconds=seconds),
                finished_at=now,
            )
        )
        await session.commit()


async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_upload_creates_task(client: AsyncClient):
    r = await client.post("/api/classify-zip/", files=_zip_file())
    assert r.status_code == 200
    data = r.json()
    assert "task_id" in data
    assert data["deduplicated"] is False


async def test_duplicate_upload_returns_same_task(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"same"))
    r2 = await client.post("/api/classify-zip/", files=_zip_file(b"same"))

    assert r1.json()["deduplicated"] is False
    assert r2.json()["deduplicated"] is True
    assert r1.json()["task_id"] == r2.json()["task_id"]


async def test_deduplicated_upload_does_not_start_processing(client: AsyncClient, monkeypatch):
    """Ключевая гарантия идемпотентности: повтор не запускает обработку."""
    calls: list[str] = []

    async def spy(task_id: str) -> None:
        calls.append(task_id)

    monkeypatch.setattr("app.routers.upload.process_task", spy)

    await client.post("/api/classify-zip/", files=_zip_file(b"idem"))
    assert len(calls) == 1
    await client.post("/api/classify-zip/", files=_zip_file(b"idem"))
    assert len(calls) == 1


async def test_different_files_create_separate_tasks(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"file_a"))
    r2 = await client.post("/api/classify-zip/", files=_zip_file(b"file_b"))

    assert r1.json()["deduplicated"] is False
    assert r2.json()["deduplicated"] is False
    assert r1.json()["task_id"] != r2.json()["task_id"]


async def test_force_bypasses_dedup(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"data"))
    r2 = await client.post("/api/classify-zip/?force=true", files=_zip_file(b"data"))

    assert r2.json()["deduplicated"] is False
    assert r1.json()["task_id"] != r2.json()["task_id"]


async def test_force_creates_new_task_each_time(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/?force=true", files=_zip_file(b"f"))
    r2 = await client.post("/api/classify-zip/?force=true", files=_zip_file(b"f"))

    ids = {r1.json()["task_id"], r2.json()["task_id"]}
    assert len(ids) == 2
    async with session_factory() as session:
        rows = (await session.execute(select(Task).where(Task.id.in_(ids)))).scalars().all()
    assert len(rows) == 2
    assert all(t.archive_sha256 is None for t in rows)


async def test_upload_after_error_creates_new_task(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"err"))
    task_id = r1.json()["task_id"]

    async with session_factory() as session:
        await session.execute(
            update(Task).where(Task.id == task_id).values(status=TaskStatus.ERROR)
        )
        await session.commit()

    r2 = await client.post("/api/classify-zip/", files=_zip_file(b"err"))
    assert r2.json()["deduplicated"] is False
    assert r2.json()["task_id"] != task_id


async def test_upload_too_large_rejected(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    r = await client.post("/api/classify-zip/", files=_zip_file(b"too big"))
    assert r.status_code == 413


async def test_stats_empty_db(client: AsyncClient):
    r = await client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["by_status"] == {"pending": 0, "processing": 0, "done": 0, "error": 0}
    assert data["avg_processing_seconds"] is None
    assert data["median_processing_seconds"] is None
    assert data["deduplicated_count"] == 0


async def test_stats_counts_by_status(client: AsyncClient):
    for content in (b"a", b"b", b"c"):
        await client.post("/api/classify-zip/", files=_zip_file(content))

    async with session_factory() as session:
        tasks = (await session.execute(select(Task).order_by(Task.created_at))).scalars().all()
        tasks[0].status = TaskStatus.PENDING
        tasks[1].status = TaskStatus.ERROR
        await session.commit()

    data = (await client.get("/api/stats")).json()
    assert data["total"] == 3
    assert data["by_status"] == {"pending": 1, "processing": 0, "done": 1, "error": 1}


async def test_stats_deduplicated_count(client: AsyncClient):
    await client.post("/api/classify-zip/", files=_zip_file(b"dup"))
    await client.post("/api/classify-zip/", files=_zip_file(b"dup"))
    await client.post("/api/classify-zip/", files=_zip_file(b"dup"))

    r = await client.get("/api/stats")
    assert r.json()["deduplicated_count"] == 2


async def test_stats_processing_time(client: AsyncClient):
    r = await client.post("/api/classify-zip/", files=_zip_file(b"done_task"))
    await _mark_done(r.json()["task_id"], seconds=10)

    data = (await client.get("/api/stats")).json()
    assert data["avg_processing_seconds"] == pytest.approx(10, abs=1)
    assert data["median_processing_seconds"] == pytest.approx(10, abs=1)


async def test_stats_median_uses_real_duration_order(client: AsyncClient):
    """Медиана должна сортировать по реальной длительности, а не по порядку вставки."""
    for content in (b"m1", b"m2", b"m3"):
        await client.post("/api/classify-zip/", files=_zip_file(content))

    # Длительности в порядке создания: 100s, 1s, 5s -> истинная медиана 5s.
    now = datetime.now(UTC)
    async with session_factory() as session:
        tasks = (await session.execute(select(Task).order_by(Task.created_at))).scalars().all()
        for task, seconds in zip(tasks, [100, 1, 5], strict=True):
            await session.execute(
                update(Task)
                .where(Task.id == task.id)
                .values(
                    status=TaskStatus.DONE,
                    created_at=now - timedelta(seconds=seconds),
                    finished_at=now,
                )
            )
        await session.commit()

    data = (await client.get("/api/stats")).json()
    assert data["median_processing_seconds"] == pytest.approx(5, abs=0.5)


async def test_stats_median_even_count(client: AsyncClient):
    for content in (b"e1", b"e2", b"e3", b"e4"):
        await client.post("/api/classify-zip/", files=_zip_file(content))

    # sorted: 10,20,30,40 -> медиана = (20+30)/2 = 25.
    now = datetime.now(UTC)
    async with session_factory() as session:
        tasks = (await session.execute(select(Task).order_by(Task.created_at))).scalars().all()
        for task, seconds in zip(tasks, [40, 10, 30, 20], strict=True):
            await session.execute(
                update(Task)
                .where(Task.id == task.id)
                .values(
                    status=TaskStatus.DONE,
                    created_at=now - timedelta(seconds=seconds),
                    finished_at=now,
                )
            )
        await session.commit()

    data = (await client.get("/api/stats")).json()
    assert data["median_processing_seconds"] == pytest.approx(25, abs=0.5)


async def test_stats_zero_duration_is_not_null(client: AsyncClient):
    r = await client.post("/api/classify-zip/", files=_zip_file(b"instant"))
    await _mark_done(r.json()["task_id"], seconds=0)

    data = (await client.get("/api/stats")).json()
    assert data["avg_processing_seconds"] == 0.0
    assert data["median_processing_seconds"] == 0.0
