"""
Модель задачи обработки. Для локального стенда - sqlite (по условию задания, без
внешней инфраструктуры). Агрегаты статистики в repositories.py используют sqlite-only
julianday(); для PostgreSQL их нужно переписать на extract(epoch ...)/percentile_cont.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archive_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    dedup_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
