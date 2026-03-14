import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_metrics_returns_prometheus_text(monkeypatch, client):
    import routers.metrics as metrics_router

    monkeypatch.setattr(metrics_router, "get_request_count", lambda: 7)
    monkeypatch.setattr(
        metrics_router,
        "get_task_stats",
        lambda: {
            "active_tasks": 2,
            "alive_tasks": 2,
            "stuck_tasks": 0,
            "submitted_tasks": 4,
            "completed_tasks": 1,
            "failed_tasks": 1,
            "cancelled_tasks": 0,
            "status": "healthy",
        },
    )

    async def db_ok(*_args, **_kwargs):
        return True

    monkeypatch.setattr(metrics_router, "check_database_connection", db_ok)

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    assert "kra_requests_total 7" in text
    assert "kra_background_tasks_active 2" in text
    assert "kra_background_tasks_failed_total 1" in text
    assert "kra_database_up 1" in text
    assert "kra_uptime_seconds " in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_metrics_returns_404_when_disabled(monkeypatch, client):
    import routers.metrics as metrics_router

    monkeypatch.setattr(metrics_router.settings, "prometheus_enabled", False)

    response = await client.get("/metrics")

    assert response.status_code == 404
