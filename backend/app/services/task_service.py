"""Бизнес-логика обработки загрузок и статистики."""

import asyncio
import hashlib
import logging
import uuid

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db import engine
from app.db.models import Task, TaskStatus, utcnow
from app.db.repositories import TaskRepository
from app.schemas import StatsResponse, StatusCounts, UploadResponse

logger = logging.getLogger(__name__)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def process_task(task_id: str) -> None:
    """Заглушка дорогой обработки (LLM/OCR). В проде - отдельный воркер/очередь.

    Запускается в фоне после ответа, поэтому открывает собственную сессию.
    """
    try:
        await asyncio.sleep(settings.processing_delay_seconds)
        async with engine.async_session() as session:
            await session.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(status=TaskStatus.DONE, finished_at=utcnow())
            )
            await session.commit()
        logger.info("Processed task: task_id=%s", task_id)
    except Exception:
        logger.exception("Processing failed: task_id=%s", task_id)
        await _mark_error(task_id)


async def _mark_error(task_id: str) -> None:
    async with engine.async_session() as session:
        await session.execute(
            update(Task).where(Task.id == task_id).values(status=TaskStatus.ERROR)
        )
        await session.commit()


class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self.repo = repo

    async def classify_zip(
        self, *, content: bytes, filename: str, force: bool
    ) -> tuple[UploadResponse, bool]:
        """Идемпотентная загрузка. Возвращает (ответ, нужно_ли_запускать_обработку)."""
        archive_sha256 = compute_sha256(content)

        if not force:
            duplicate = await self._try_dedup(archive_sha256)
            if duplicate is not None:
                return duplicate, False

        await self.repo.clear_hash_for_errored(archive_sha256)
        task = Task(
            id=str(uuid.uuid4()),
            original_filename=filename,
            status=TaskStatus.PROCESSING,
            archive_sha256=None if force else archive_sha256,
        )
        try:
            await self.repo.create(task)
        except IntegrityError:
            # Гонка: параллельная загрузка того же архива заняла unique index.
            await self.repo.rollback()
            duplicate = await self._try_dedup(archive_sha256)
            if duplicate is not None:
                return duplicate, False
            raise

        logger.info("Created task: task_id=%s sha256=%s", task.id, archive_sha256)
        return UploadResponse(task_id=task.id, deduplicated=False), True

    async def _try_dedup(self, archive_sha256: str) -> UploadResponse | None:
        existing = await self.repo.get_active_by_hash(archive_sha256)
        if existing is None:
            return None
        await self.repo.increment_dedup_count(existing.id)
        logger.info("Deduplicated upload: task_id=%s sha256=%s", existing.id, archive_sha256)
        return UploadResponse(task_id=existing.id, deduplicated=True)

    async def get_stats(self) -> StatsResponse:
        agg = await self.repo.get_stats()
        return StatsResponse(
            total=agg.total,
            by_status=StatusCounts(
                pending=agg.pending,
                processing=agg.processing,
                done=agg.done,
                error=agg.error,
            ),
            avg_processing_seconds=agg.avg_processing_seconds,
            median_processing_seconds=agg.median_processing_seconds,
            deduplicated_count=agg.deduplicated_count,
        )
