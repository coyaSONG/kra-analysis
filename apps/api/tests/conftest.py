"""
pytest configuration and fixtures for KRA API v2 tests
"""

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_asyncio
import redis.asyncio as redis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from config import Settings
from infrastructure.database import Base, get_db
from infrastructure.redis_client import get_redis

# Import application components
from main_v2 import app
from models.database_models import APIKey


# Test configuration
@pytest.fixture(scope="session")
def test_settings():
    """Test-specific settings"""
    s = Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",  # Use test DB
        secret_key="test-secret-key-for-testing-only",
        valid_api_keys=["test-api-key-123", "test-api-key-456"],
        debug=True,
        kra_api_key="test-kra-api-key",
    )
    # Propagate settings to global singleton for modules that import config.settings
    import config as global_config

    global_config.settings.environment = s.environment
    global_config.settings.database_url = s.database_url
    global_config.settings.redis_url = s.redis_url
    global_config.settings.secret_key = s.secret_key
    global_config.settings.valid_api_keys = s.valid_api_keys
    global_config.settings.debug = s.debug
    global_config.settings.kra_api_key = s.kra_api_key

    return s


# Event loop configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
@pytest_asyncio.fixture(scope="function")
async def test_db_engine(test_settings):
    """Create a test database engine"""
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
    """Create a test database session"""
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


# Redis fixtures
@pytest_asyncio.fixture(scope="function")
async def redis_client(test_settings):
    """Create a test Redis client"""
    # Try to connect to real Redis, fall back to mock if unavailable
    try:
        client = await redis.from_url(
            test_settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        # Test connection
        await client.ping()
        # Clear test database
        await client.flushdb()

        yield client

        await client.flushdb()
        await client.close()
    except (redis.ConnectionError, redis.TimeoutError, ConnectionRefusedError):
        # Fall back to mock Redis
        from tests.utils.mocks import MockRedisClient

        mock_client = MockRedisClient()
        yield mock_client


# API client fixtures
@pytest_asyncio.fixture(scope="function")
async def client(db_session, redis_client):
    """Create a test API client with dependency overrides"""

    # Override dependencies
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    # Use ASGI transport for async testing
    from httpx import ASGITransport

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(client, db_session):
    """Create an authenticated test API client"""
    # Create test API key in database
    api_key = APIKey(
        key="test-api-key-123",
        name="Test API Key",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(api_key)
    await db_session.commit()

    # Add authentication header
    client.headers["X-API-Key"] = "test-api-key-123"

    yield client


@pytest.fixture
def sample_race_data():
    """Sample race data"""
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


# Mock fixtures
@pytest.fixture
def mock_kra_api_response():
    """Mock KRA API response"""
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


# Utility fixtures
@pytest.fixture
def anyio_backend():
    """Specify asyncio backend for anyio"""
    return "asyncio"


@pytest_asyncio.fixture
async def clean_db(db_session):
    """Clean database before test"""
    # Delete all data from tables
    await db_session.execute("DELETE FROM api_keys")
    await db_session.execute("DELETE FROM jobs")
    await db_session.execute("DELETE FROM job_logs")
    await db_session.execute("DELETE FROM races")
    await db_session.execute("DELETE FROM predictions")
    await db_session.execute("DELETE FROM prompt_templates")
    await db_session.commit()
    yield
    # Cleanup is handled by fixture teardown
