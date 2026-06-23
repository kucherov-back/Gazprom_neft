"""Async engine + sessionmaker (sqlite для простоты локального запуска)."""
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base

DATABASE_URL = "sqlite+aiosqlite:///./stand.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Создаём таблицы автоматически для удобства локального запуска."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with async_session() as session:
        yield session
