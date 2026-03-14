import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_health_uses_background_task_status(
    monkeypatch, authenticated_client
):
    import routers.health as health_router

    monkeypatch.setattr(
        health_router,
        "get_task_stats",
        lambda: {
            "active_tasks": 2,
            "alive_tasks": 1,
            "stuck_tasks": 1,
            "submitted_tasks": 3,
            "completed_tasks": 1,
            "failed_tasks": 1,
            "cancelled_tasks": 0,
            "status": "degraded",
        },
    )

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["background_tasks"] == "degraded"
    assert data["status"] == "degraded"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_health_reports_healthy_background_tasks(
    monkeypatch, authenticated_client
):
    import routers.health as health_router

    monkeypatch.setattr(
        health_router,
        "get_task_stats",
        lambda: {
            "active_tasks": 0,
            "alive_tasks": 0,
            "stuck_tasks": 0,
            "submitted_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "status": "healthy",
        },
    )

    response = await authenticated_client.get("/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["background_tasks"] == "healthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"
