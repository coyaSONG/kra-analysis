import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_metrics_returns_prometheus_text(monkeypatch, client, api_app):
    import routers.metrics as metrics_router
    from bootstrap.runtime import AppRuntime, ObservabilityFacade, get_runtime

    class FakeObservability(ObservabilityFacade):
        def render_metrics(self, *, db_ok: bool, now: float | None = None) -> str:
            task_stats = {
                "active_tasks": 2,
                "alive_tasks": 2,
                "stuck_tasks": 0,
                "submitted_tasks": 4,
                "completed_tasks": 1,
                "failed_tasks": 1,
                "cancelled_tasks": 0,
                "status": "healthy",
            }
            lines = [
                "# HELP kra_requests_total Total HTTP requests processed",
                "# TYPE kra_requests_total counter",
                "kra_requests_total 7",
                "# HELP kra_background_tasks_active Current active background tasks",
                "# TYPE kra_background_tasks_active gauge",
                f"kra_background_tasks_active {task_stats['active_tasks']}",
                "# HELP kra_background_tasks_failed_total Total failed background tasks",
                "# TYPE kra_background_tasks_failed_total counter",
                f"kra_background_tasks_failed_total {task_stats['failed_tasks']}",
                "# HELP kra_database_up Database connectivity status",
                "# TYPE kra_database_up gauge",
                f"kra_database_up {1 if db_ok else 0}",
                "# HELP kra_uptime_seconds Process uptime in seconds",
                "# TYPE kra_uptime_seconds gauge",
                "kra_uptime_seconds 12.34",
            ]
            return "\n".join(lines) + "\n"

    async def db_ok(*_args, **_kwargs):
        return True

    monkeypatch.setattr(metrics_router, "check_database_connection", db_ok)
    api_app.dependency_overrides[get_runtime] = lambda: AppRuntime(
        settings=metrics_router.settings, observability=FakeObservability()
    )

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
