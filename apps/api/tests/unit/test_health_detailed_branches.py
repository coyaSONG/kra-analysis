import pytest


class FailPing:
    def ping(self):
        raise RuntimeError("fail")


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_health_redis_unhealthy(api_app, authenticated_client):
    # Override dependency to simulate redis with failing ping
    def override():
        return FailPing()

    # FastAPI override
    import routers.health as health_router

    api_app.dependency_overrides[health_router.get_optional_redis] = override
    try:
        r = await authenticated_client.get("/health/detailed")
        assert r.status_code == 200
        data = r.json()
        assert data["redis"] == "unhealthy"
    finally:
        api_app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_health_db_unhealthy(monkeypatch, authenticated_client):
    # Patch DB health to False
    import routers.health as health_router

    async def bad_db(*_args, **_kwargs):
        return False

    monkeypatch.setattr(health_router, "check_database_connection", bad_db)

    r = await authenticated_client.get("/health/detailed")
    assert r.status_code == 200
    data = r.json()
    assert data["database"] == "unhealthy"
