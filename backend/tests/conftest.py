"""Pytest fixtures: test app, db, client, auth."""
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Use in-memory SQLite for tests (must set before importing app)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("MIN_ATS_SCORE", "0")  # Allow any score in tests

from main import app
from database.connection import get_db, engine
from database.base import Base
import models  # noqa: F401

TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Authenticated client: overrides get_db and get_current_user (after auth_headers)."""
    from api.deps import get_current_user
    from models.user import User

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    async def override_get_current_user():
        result = await db_session.execute(select(User).where(User.email == "test@example.com").limit(1))
        user = result.scalar_one_or_none()
        if not user:
            pytest.skip("test user not created")
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_no_auth(db_session: AsyncSession):
    """Client with only get_db overridden; auth endpoints will return 401 without token."""
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    """Register, login, return Authorization header."""
    r = await client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    if r.status_code != 200:
        r = await client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "testpass123"},
        )
    assert r.status_code == 200
    data = r.json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}
