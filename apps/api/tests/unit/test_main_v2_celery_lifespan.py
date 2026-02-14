import pytest
from httpx import ASGITransport, AsyncClient

import main_v2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_starts_successfully():
    """Test that the application lifespan starts successfully."""
    transport = ASGITransport(app=main_v2.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_redis_init_fail(monkeypatch):
    import infrastructure.redis_client as rc

    async def boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(rc, "init_redis", boom)

    transport = ASGITransport(app=main_v2.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
