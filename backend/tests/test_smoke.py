import io
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.db.models import Task, TaskStatus
from tests.conftest import test_session_factory


def _zip_file(content: bytes = b"hello", name: str = "a.zip"):
    return {"file": (name, io.BytesIO(content), "application/zip")}


@pytest.mark.asyncio
async def test_upload_creates_task(client: AsyncClient):
    r = await client.post("/api/classify-zip/", files=_zip_file())
    assert r.status_code == 200
    data = r.json()
    assert "task_id" in data
    assert data["deduplicated"] is False


@pytest.mark.asyncio
async def test_duplicate_upload_returns_same_task(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"same"))
    r2 = await client.post("/api/classify-zip/", files=_zip_file(b"same"))

    assert r1.json()["deduplicated"] is False
    assert r2.json()["deduplicated"] is True
    assert r1.json()["task_id"] == r2.json()["task_id"]


@pytest.mark.asyncio
async def test_different_files_create_separate_tasks(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"file_a"))
    r2 = await client.post("/api/classify-zip/", files=_zip_file(b"file_b"))

    assert r1.json()["deduplicated"] is False
    assert r2.json()["deduplicated"] is False
    assert r1.json()["task_id"] != r2.json()["task_id"]


@pytest.mark.asyncio
async def test_force_bypasses_dedup(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"data"))
    r2 = await client.post("/api/classify-zip/?force=true", files=_zip_file(b"data"))

    assert r2.json()["deduplicated"] is False
    assert r1.json()["task_id"] != r2.json()["task_id"]


@pytest.mark.asyncio
async def test_upload_after_error_creates_new_task(client: AsyncClient):
    r1 = await client.post("/api/classify-zip/", files=_zip_file(b"err"))
    task_id = r1.json()["task_id"]

    async with test_session_factory() as session:
        await session.execute(
            update(Task).where(Task.id == task_id).values(status=TaskStatus.ERROR)
        )
        await session.commit()

    r2 = await client.post("/api/classify-zip/", files=_zip_file(b"err"))
    assert r2.json()["deduplicated"] is False
    assert r2.json()["task_id"] != task_id


@pytest.mark.asyncio
async def test_stats_empty_db(client: AsyncClient):
    r = await client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["by_status"] == {"pending": 0, "processing": 0, "done": 0, "error": 0}
    assert data["avg_processing_seconds"] is None
    assert data["median_processing_seconds"] is None
    assert data["deduplicated_count"] == 0


@pytest.mark.asyncio
async def test_stats_counts_by_status(client: AsyncClient):
    await client.post("/api/classify-zip/", files=_zip_file(b"one"))
    await client.post("/api/classify-zip/", files=_zip_file(b"two"))

    r = await client.get("/api/stats")
    data = r.json()
    assert data["total"] == 2
    assert data["by_status"]["processing"] == 2


@pytest.mark.asyncio
async def test_stats_deduplicated_count(client: AsyncClient):
    await client.post("/api/classify-zip/", files=_zip_file(b"dup"))
    await client.post("/api/classify-zip/", files=_zip_file(b"dup"))
    await client.post("/api/classify-zip/", files=_zip_file(b"dup"))

    r = await client.get("/api/stats")
    assert r.json()["deduplicated_count"] == 2


@pytest.mark.asyncio
async def test_stats_processing_time(client: AsyncClient):
    await client.post("/api/classify-zip/", files=_zip_file(b"done_task"))

    now = datetime.utcnow()
    async with test_session_factory() as session:
        await session.execute(
            update(Task).values(
                status=TaskStatus.DONE,
                created_at=now - timedelta(seconds=10),
                finished_at=now,
            )
        )
        await session.commit()

    r = await client.get("/api/stats")
    data = r.json()
    assert data["avg_processing_seconds"] is not None
    assert 9.0 <= data["avg_processing_seconds"] <= 11.0
    assert data["median_processing_seconds"] is not None
    assert 9.0 <= data["median_processing_seconds"] <= 11.0