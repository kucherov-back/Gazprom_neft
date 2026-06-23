"""Слой доступа к данным: только работа с БД, без бизнес-правил."""

from dataclasses import dataclass

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task, TaskStatus


@dataclass(frozen=True, slots=True)
class StatsAggregate:
    """Результат агрегации статистики (доменный объект, не API-схема)."""

    total: int
    pending: int
    processing: int
    done: int
    error: int
    avg_processing_seconds: float | None
    median_processing_seconds: float | None
    deduplicated_count: int


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def rollback(self) -> None:
        await self.session.rollback()

    async def get_active_by_hash(self, archive_sha256: str) -> Task | None:
        """Не-ERROR задача с этим хэшем - кандидат на дедупликацию."""
        stmt = select(Task).where(
            Task.archive_sha256 == archive_sha256,
            Task.status != TaskStatus.ERROR,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def clear_hash_for_errored(self, archive_sha256: str) -> None:
        """Освобождаем хэш у ERROR-задач, чтобы unique index не мешал повторной загрузке."""
        stmt = (
            update(Task)
            .where(Task.archive_sha256 == archive_sha256, Task.status == TaskStatus.ERROR)
            .values(archive_sha256=None)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def increment_dedup_count(self, task_id: str) -> None:
        stmt = update(Task).where(Task.id == task_id).values(dedup_count=Task.dedup_count + 1)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_stats(self) -> StatsAggregate:
        """Все агрегаты одним SQL-запросом (агрегация в БД). Медиана - оконной функцией.

        sqlite-only: julianday(). Для PostgreSQL заменить на extract(epoch ...) и
        percentile_cont(0.5) within group (order by ...).
        """
        duration = (func.julianday(Task.finished_at) - func.julianday(Task.created_at)) * 86400
        done = and_(Task.status == TaskStatus.DONE, Task.finished_at.is_not(None))

        # Подзапрос с порядковым номером строки по реальной длительности обработки.
        ranked = (
            select(
                duration.label("seconds"),
                func.row_number().over(order_by=duration).label("rn"),
                func.count().over().label("cnt"),
            )
            .where(done)
            .subquery()
        )
        # Медиана = среднее одной/двух центральных строк. self_group() сохраняет скобки
        # вокруг (cnt + n), иначе приоритет op('/') даёт `cnt + n / 2`. op('/') = целочисленное.
        lower = (ranked.c.cnt + 1).self_group().op("/")(2)
        upper = (ranked.c.cnt + 2).self_group().op("/")(2)
        median = (
            select(func.avg(ranked.c.seconds))
            .where(ranked.c.rn.in_([lower, upper]))
            .scalar_subquery()
        )

        def count_of(status: TaskStatus):
            return func.coalesce(func.sum(case((Task.status == status, 1), else_=0)), 0)

        stmt = select(
            func.count().label("total"),
            count_of(TaskStatus.PENDING).label("pending"),
            count_of(TaskStatus.PROCESSING).label("processing"),
            count_of(TaskStatus.DONE).label("done"),
            count_of(TaskStatus.ERROR).label("error"),
            func.avg(case((done, duration))).label("avg_seconds"),
            func.coalesce(func.sum(Task.dedup_count), 0).label("deduplicated_count"),
            median.label("median_seconds"),
        )
        row = (await self.session.execute(stmt)).one()

        def rounded(value: float | None) -> float | None:
            return round(value, 2) if value is not None else None

        return StatsAggregate(
            total=row.total,
            pending=row.pending,
            processing=row.processing,
            done=row.done,
            error=row.error,
            avg_processing_seconds=rounded(row.avg_seconds),
            median_processing_seconds=rounded(row.median_seconds),
            deduplicated_count=row.deduplicated_count,
        )
