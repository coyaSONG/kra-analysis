import pytest


class _FailedTask:
    def done(self):
        return True

    def cancelled(self):
        return False

    def exception(self):
        return RuntimeError("boom")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_detailed_health_background_tasks_healthy_from_registry(
    monkeypatch, authenticated_client
):
    import infrastructure.background_tasks as bg_tasks

    monkeypatch.setattr(bg_tasks, "_running_tasks", {})

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["background_tasks"] == "healthy"
    assert {
        "status",
        "database",
        "redis",
        "background_tasks",
        "timestamp",
        "version",
    }.issubset(data.keys())


@pytest.mark.asyncio
@pytest.mark.unit
async def test_detailed_health_background_tasks_degraded_from_registry(
    monkeypatch, authenticated_client
):
    import infrastructure.background_tasks as bg_tasks
    import main_v2
    from infrastructure.redis_client import get_redis

    class _HealthyRedis:
        async def ping(self):
            return True

    async def _override_get_redis():
        yield _HealthyRedis()

    async def _db_ok(_db):
        return True

    monkeypatch.setattr(bg_tasks, "_running_tasks", {"task-1": _FailedTask()})
    monkeypatch.setattr(main_v2, "check_database_connection", _db_ok)
    main_v2.app.dependency_overrides[get_redis] = _override_get_redis

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["background_tasks"] == "degraded"
    assert data["status"] in {"degraded", "unhealthy"}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_detailed_health_degraded_when_redis_unhealthy_but_db_healthy(
    monkeypatch, authenticated_client
):
    import main_v2
    from infrastructure.redis_client import get_redis

    class _BrokenRedis:
        async def ping(self):
            raise RuntimeError("redis unavailable")

    async def _override_get_redis():
        yield _BrokenRedis()

    async def _db_ok(_db):
        return True

    monkeypatch.setattr(main_v2, "check_database_connection", _db_ok)
    main_v2.app.dependency_overrides[get_redis] = _override_get_redis

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "healthy"
    assert data["redis"] == "unhealthy"
    assert data["status"] in {"degraded", "unhealthy"}
