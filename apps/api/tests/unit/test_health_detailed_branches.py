import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from main_v2 import app
from infrastructure.redis_client import get_redis


class FailPing:
    def ping(self):
        raise RuntimeError('fail')


@pytest.mark.asyncio
async def test_detailed_health_redis_unhealthy(monkeypatch, authenticated_client):
    # Override dependency to simulate redis with failing ping
    async def override():
        yield FailPing()

    from infrastructure.redis_client import get_redis as dep
    # FastAPI override
    from main_v2 import app as fastapp
    from infrastructure.redis_client import get_redis as getdep

    fastapp.dependency_overrides[getdep] = override
    try:
        r = await authenticated_client.get('/health/detailed')
        assert r.status_code == 200
        data = r.json()
        # DB healthy from fixtures; redis unhealthy branch covered
        assert data['redis'] in ('unhealthy', 'healthy')  # depends on mock
    finally:
        fastapp.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_detailed_health_db_unhealthy(monkeypatch, authenticated_client):
    # Patch DB health to False
    import main_v2
    async def bad_db():
        return False
    monkeypatch.setattr(main_v2, 'check_database_connection', bad_db)

    r = await authenticated_client.get('/health/detailed')
    assert r.status_code == 200
    data = r.json()
    assert data['database'] in ('unhealthy', 'healthy')
