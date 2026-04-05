import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_health_uses_background_task_status(
    authenticated_client, api_app
):
    import routers.health as health_router
    from bootstrap.runtime import AppRuntime, ObservabilityFacade, get_runtime

    class FakeObservability(ObservabilityFacade):
        def build_health_snapshot(
            self,
            *,
            db_ok: bool,
            redis_status: str,
            background_status: str,
            version: str,
            now: float | None = None,
        ) -> dict:
            return {
                "status": "degraded",
                "database": "healthy" if db_ok else "unhealthy",
                "redis": redis_status,
                "background_tasks": background_status,
                "timestamp": 1.0,
                "version": version,
            }

    task_stats = {
        "active_tasks": 2,
        "alive_tasks": 1,
        "stuck_tasks": 1,
        "submitted_tasks": 3,
        "completed_tasks": 1,
        "failed_tasks": 1,
        "cancelled_tasks": 0,
        "status": "degraded",
    }
    api_app.dependency_overrides[get_runtime] = lambda: AppRuntime(
        settings=health_router.settings,
        observability=FakeObservability(task_stats_provider=lambda: task_stats),
    )

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["background_tasks"] == "degraded"
    assert data["status"] == "degraded"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_health_reports_healthy_background_tasks(
    authenticated_client, api_app
):
    import routers.health as health_router
    from bootstrap.runtime import AppRuntime, ObservabilityFacade, get_runtime

    task_stats = {
        "active_tasks": 0,
        "alive_tasks": 0,
        "stuck_tasks": 0,
        "submitted_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "cancelled_tasks": 0,
        "status": "healthy",
    }
    api_app.dependency_overrides[get_runtime] = lambda: AppRuntime(
        settings=health_router.settings,
        observability=ObservabilityFacade(task_stats_provider=lambda: task_stats),
    )

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["background_tasks"] == "healthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"
    assert data["status"] == "healthy"
