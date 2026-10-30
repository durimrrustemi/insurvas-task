from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db import get_session
from app.main import app
from app.models import Base
from app.settings import settings


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(settings.database_url_test, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """One outer transaction per test, rolled back at teardown.

    Code under test may call session.commit(); with create_savepoint those commits
    only release a savepoint, so nothing outlives the test.
    """
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        s = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield s
        finally:
            await s.close()
            await trans.rollback()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = _override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()
