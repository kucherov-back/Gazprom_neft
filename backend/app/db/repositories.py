from sqlalchemy import select, update, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task, TaskStatus


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get(self, task_id: str) -> Task | None:
        return await self.session.get(Task, task_id)

    async def list_all(self) -> list[Task]:
        res = await self.session.execute(select(Task))
        return list(res.scalars().all())

    async def get_by_hash(self, archive_sha256: str) -> Task | None:
        stmt = select(Task).where(
            Task.archive_sha256 == archive_sha256,
            Task.status != TaskStatus.ERROR,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def clear_hash_for_errored(self, archive_sha256: str) -> None:
        stmt = (
            update(Task)
            .where(
                Task.archive_sha256 == archive_sha256,
                Task.status == TaskStatus.ERROR,
            )
            .values(archive_sha256=None)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def increment_dedup_count(self, task_id: str) -> None:
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(dedup_count=Task.dedup_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_stats(self) -> dict:
        done_time = func.julianday(Task.finished_at) - func.julianday(Task.created_at)
        done_seconds = done_time * 86400

        stmt = select(
            func.count().label("total"),
            func.sum(case((Task.status == TaskStatus.PENDING, 1), else_=0)).label("pending"),
            func.sum(case((Task.status == TaskStatus.PROCESSING, 1), else_=0)).label("processing"),
            func.sum(case((Task.status == TaskStatus.DONE, 1), else_=0)).label("done"),
            func.sum(case((Task.status == TaskStatus.ERROR, 1), else_=0)).label("error"),
            func.avg(case(
                (Task.status == TaskStatus.DONE, done_seconds),
                else_=None,
            )).label("avg_processing_seconds"),
            func.sum(Task.dedup_count).label("deduplicated_count"),
        )

        result = await self.session.execute(stmt)
        row = result.one()

        median_stmt = text("""
            SELECT AVG(processing_seconds) as median_processing_seconds
            FROM (
                SELECT
                    (julianday(finished_at) - julianday(created_at)) * 86400 AS processing_seconds,
                    ROW_NUMBER() OVER (ORDER BY finished_at - created_at) AS rn,
                    COUNT(*) OVER () AS cnt
                FROM tasks
                WHERE status = 'DONE' AND finished_at IS NOT NULL
            )
            WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
        """)
        median_result = await self.session.execute(median_stmt)
        median_row = median_result.one()

        return {
            "total": row.total or 0,
            "by_status": {
                "pending": row.pending or 0,
                "processing": row.processing or 0,
                "done": row.done or 0,
                "error": row.error or 0,
            },
            "avg_processing_seconds": round(row.avg_processing_seconds, 2) if row.avg_processing_seconds else None,
            "median_processing_seconds": round(median_row.median_processing_seconds, 2) if median_row.median_processing_seconds else None,
            "deduplicated_count": row.deduplicated_count or 0,
        }