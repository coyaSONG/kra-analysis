import pytest


class FailPing:
    def ping(self):
        raise RuntimeError("fail")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_detailed_health_redis_error(api_app, authenticated_client):
    import routers.health as health_router

    api_app.dependency_overrides[health_router.get_optional_redis] = lambda: FailPing()
    try:
        response = await authenticated_client.get("/health/detailed")
    finally:
        api_app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "error"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_detailed_health_redis_unavailable_when_dependency_missing(
    api_app, authenticated_client
):
    import routers.health as health_router

    api_app.dependency_overrides[health_router.get_optional_redis] = lambda: None
    try:
        response = await authenticated_client.get("/health/detailed")
    finally:
        api_app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "unavailable"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_detailed_health_fake_redis_without_ping_is_unavailable(
    api_app, authenticated_client
):
    import routers.health as health_router

    api_app.dependency_overrides[health_router.get_optional_redis] = lambda: object()
    try:
        response = await authenticated_client.get("/health/detailed")
    finally:
        api_app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "unavailable"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_detailed_health_db_unhealthy(monkeypatch, authenticated_client):
    import routers.health as health_router

    async def bad_db(*_args, **_kwargs):
        return False

    monkeypatch.setattr(health_router, "check_database_connection", bad_db)

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "unhealthy"
