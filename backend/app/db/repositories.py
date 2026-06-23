from sqlalchemy import select, update
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