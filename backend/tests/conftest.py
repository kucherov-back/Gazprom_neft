import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import engine as engine_module
from app.db.models import Base
from app.main import app

# StaticPool + общий in-memory: одна БД на все соединения внутри теста.
test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
session_factory = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch):
    # И HTTP-эндпоинты, и фоновая обработка должны ходить в одну тестовую БД.
    monkeypatch.setattr(engine_module, "async_session", session_factory)
    monkeypatch.setattr(settings, "processing_delay_seconds", 0)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Закрываем in-memory соединение, иначе фоновый поток aiosqlite держит процесс.
    await test_engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
