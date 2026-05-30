"""Shared fixtures for all tests."""
import asyncio
import os
import pytest
from pathlib import Path
from collections.abc import AsyncGenerator

# Start PG container BEFORE any app import — settings needs DATABASE_URL at import time
from testcontainers.postgres import PostgresContainer

CONFIGS_DIR = Path(__file__).parent.parent / "app" / "situations" / "configs"

_pg = PostgresContainer("postgres:16-alpine")
_pg.start()

_raw_url = _pg.get_connection_url()
_db_url = (
    _raw_url.replace("+psycopg2", "+asyncpg")
    if "+psycopg2" in _raw_url
    else _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
)

os.environ["SECRET_KEY"] = "a" * 64
os.environ["DATABASE_URL"] = _db_url
os.environ["APP_ENV"] = "development"

from cryptography.fernet import Fernet
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())


def pytest_sessionfinish(session, exitstatus):
    _pg.stop()


# App imports after env vars are set
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from httpx import AsyncClient, ASGITransport

from app.core.database import Base, get_db
from app.main import app
from app.models.document import Document  # noqa: F401 — register with Base.metadata
from app.models.audit_log import AuditLog  # noqa: F401 — register with Base.metadata
from app.models.order import Order
from app.models.user import User
from app.situations.registry import registry
from app.core.security import create_access_token

_test_engine = create_async_engine(_db_url, echo=False)
_TestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)

_TRUNCATE_ORDER = ["documents", "orders", "users"]


async def _create_all():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Create tables once synchronously before any test event loop is started.
# dispose() clears the connection pool so each test gets fresh connections
# in its own function-scoped event loop — avoids "Future attached to different loop".
asyncio.run(_create_all())
_test_engine.sync_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def load_registry():
    registry.load(CONFIGS_DIR)
    yield


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _TestSessionLocal() as session:
        yield session
    async with _test_engine.begin() as conn:
        for table in _TRUNCATE_ORDER:
            await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
    # Dispose pool so the next test (in its own event loop) starts with
    # fresh asyncpg connections — avoids "Future attached to different loop".
    _test_engine.sync_engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    del app.dependency_overrides[get_db]


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    u = User(email="test@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token() -> str:
    from app.api.v1.reviews import create_admin_token
    return create_admin_token()
