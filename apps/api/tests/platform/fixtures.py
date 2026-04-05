"""
Shared pytest fixtures for apps/api tests.
"""

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from config import Settings
from infrastructure.database import Base, get_db
from infrastructure.redis_client import get_redis
from main_v2 import create_app
from models.database_models import APIKey
from routers.health import get_optional_redis
from tests.platform.fakes import ControlledTaskRunner, FakeRedis, InlineTaskRunner


def _apply_test_settings_to_global(settings_obj: Settings) -> None:
    """Update the config singleton used by modules importing `config.settings`."""
    import config as global_config

    global_config.settings.environment = settings_obj.environment
    global_config.settings.database_url = settings_obj.database_url
    global_config.settings.redis_url = settings_obj.redis_url
    global_config.settings.secret_key = settings_obj.secret_key
    global_config.settings.valid_api_keys = settings_obj.valid_api_keys
    global_config.settings.debug = settings_obj.debug
    global_config.settings.kra_api_key = settings_obj.kra_api_key


@pytest.fixture(scope="session")
def test_settings():
    """Test-specific settings used by the shared harness."""
    settings_obj = Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://fake/15",
        secret_key="test-secret-key-for-testing-only",
        valid_api_keys=["test-api-key-123", "test-api-key-456"],
        debug=True,
        kra_api_key="test-kra-api-key",
    )
    _apply_test_settings_to_global(settings_obj)
    return settings_obj


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async pytest fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_db_engine(test_settings):
    """Create a new ephemeral database engine for each test."""
    is_sqlite = test_settings.database_url.startswith("sqlite")
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        poolclass=StaticPool if is_sqlite else NullPool,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db_engine):
    """Create a test database session wrapped for raw SQL convenience."""
    async_session = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:

        class _SessionWrapper:
            def __init__(self, inner):
                self._inner = inner

            async def execute(self, statement, *args, **kwargs):
                from sqlalchemy import text as sql_text

                if isinstance(statement, str):
                    statement = sql_text(statement)
                return await self._inner.execute(statement, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._inner, name)

        yield _SessionWrapper(session)
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    """Return the deterministic Redis fake used across tests."""
    client = FakeRedis()
    yield client
    await client.flushdb()
    await client.close()


@pytest.fixture(scope="function")
def api_app():
    """Create a fresh app instance per test."""
    return create_app()


@pytest_asyncio.fixture(scope="function")
async def client(api_app, db_session, redis_client):
    """Create a test API client with DB and Redis overrides."""

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_client

    def override_get_optional_redis():
        return redis_client

    api_app.dependency_overrides[get_db] = override_get_db
    api_app.dependency_overrides[get_redis] = override_get_redis
    api_app.dependency_overrides[get_optional_redis] = override_get_optional_redis
    api_app.state.db_session_factory = async_sessionmaker(
        db_session.bind, class_=AsyncSession, expire_on_commit=False
    )

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    api_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(client, db_session):
    """Create an authenticated test API client using a DB-backed API key."""
    api_key = APIKey(
        key="test-api-key-123",
        name="Test API Key",
        is_active=True,
        permissions=["read", "write"],
        created_at=datetime.now(UTC),
    )
    db_session.add(api_key)
    await db_session.commit()
    client.headers["X-API-Key"] = "test-api-key-123"
    yield client


@pytest.fixture
def auth_headers_factory():
    """Build auth headers explicitly by identity source."""

    def _build(api_key: str) -> dict[str, str]:
        return {"X-API-Key": api_key}

    return _build


@pytest_asyncio.fixture
async def db_api_key_factory(db_session):
    """Create DB-backed API keys for tests that need real dependency behavior."""

    async def _create(
        key: str,
        *,
        name: str = "Test API Key",
        is_active: bool = True,
        daily_limit: int | None = None,
        today_requests: int = 0,
        permissions: list[str] | None = None,
    ) -> APIKey:
        api_key = APIKey(
            key=key,
            name=name,
            is_active=is_active,
            daily_limit=daily_limit,
            today_requests=today_requests,
            permissions=permissions or ["read", "write"],
            created_at=datetime.now(UTC),
        )
        db_session.add(api_key)
        await db_session.commit()
        return api_key

    return _create


@pytest.fixture
def env_api_key_headers(test_settings, auth_headers_factory):
    """Headers for the env-key path, distinct from DB-backed auth fixtures."""
    return auth_headers_factory(test_settings.valid_api_keys[0])


@pytest.fixture
def inline_task_runner():
    """Immediate task runner fake for slice tests."""
    return InlineTaskRunner()


@pytest.fixture
def controlled_task_runner():
    """Queued task runner fake for state-transition tests."""
    return ControlledTaskRunner()


@pytest_asyncio.fixture
async def clean_db(db_session):
    """Clean selected tables before a test."""
    await db_session.execute("DELETE FROM api_keys")
    await db_session.execute("DELETE FROM usage_events")
    await db_session.execute("DELETE FROM jobs")
    await db_session.execute("DELETE FROM job_logs")


@pytest.fixture
def sample_race_data():
    """Legacy sample race payload used by unit tests."""
    return {
        "race_date": "20240719",
        "meet": 1,
        "race_no": 1,
        "raw_data": {
            "race_info": {
                "response": {
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "hrNo": "001",
                                    "hrName": "Test Horse 1",
                                    "jkNo": "J001",
                                    "trNo": "T001",
                                    "win_odds": "5.5",
                                    "weight": "500",
                                    "rating": "85",
                                }
                            ]
                        }
                    }
                }
            },
            "horses": [],
        },
        "status": "collected",
    }


@pytest.fixture
def mock_kra_api_response():
    """Legacy sample KRA response used by unit tests."""
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {
                "items": {
                    "item": [
                        {
                            "rcDate": "20240719",
                            "meet": "1",
                            "rcNo": "1",
                            "hrNo": "001",
                            "hrName": "Test Horse 1",
                            "win_odds": "5.5",
                        }
                    ]
                },
                "numOfRows": 1,
                "pageNo": 1,
                "totalCount": 1,
            },
        }
    }
