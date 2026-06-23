import asyncio
import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.models import Task, TaskStatus
from app.db.repositories import TaskRepository
from app.schemas import UploadResponse, StatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


async def _fake_process(task_id: str) -> None:
    await asyncio.sleep(0.1)


def _compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@router.post("/classify-zip/", response_model=UploadResponse)
async def classify_zip(
    file: UploadFile,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
) -> UploadResponse:
    repo = TaskRepository(session)
    content = await file.read()
    archive_sha256 = _compute_sha256(content)

    if not force:
        existing = await repo.get_by_hash(archive_sha256)
        if existing:
            await repo.increment_dedup_count(existing.id)
            logger.info("Deduplicated upload: task_id=%s, sha256=%s", existing.id, archive_sha256)
            return UploadResponse(task_id=existing.id, deduplicated=True)

    await repo.clear_hash_for_errored(archive_sha256)

    task = Task(
        id=str(uuid.uuid4()),
        original_filename=file.filename or "archive.zip",
        status=TaskStatus.PROCESSING,
        archive_sha256=archive_sha256 if not force else None,
    )

    try:
        await repo.create(task)
    except IntegrityError:
        await session.rollback()
        existing = await repo.get_by_hash(archive_sha256)
        if existing:
            await repo.increment_dedup_count(existing.id)
            logger.info("Race condition resolved: task_id=%s, sha256=%s", existing.id, archive_sha256)
            return UploadResponse(task_id=existing.id, deduplicated=True)
        raise

    asyncio.create_task(_fake_process(task.id))
    logger.info("Created task: task_id=%s, sha256=%s", task.id, archive_sha256)
    return UploadResponse(task_id=task.id, deduplicated=False)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    repo = TaskRepository(session)
    stats = await repo.get_stats()
    return StatsResponse(**stats)