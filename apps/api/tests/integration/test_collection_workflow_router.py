from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_collection_sync_route_uses_workflow(authenticated_client, monkeypatch):
    from routers import collection_v2 as router

    outcome = SimpleNamespace(
        status="partial",
        message="Collected 1 races, failed 1 races",
        errors=[{"race_no": 2, "error": "boom"}],
        data=[{"race_no": 1}],
    )
    collect_mock = AsyncMock(return_value=outcome)
    monkeypatch.setattr(router.collection_module.commands, "collect_batch", collect_mock)

    response = await authenticated_client.post(
        "/api/v2/collection/",
        json={"date": "20240719", "meet": 1, "race_numbers": [1, 2]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    collect_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_collection_async_route_uses_workflow(authenticated_client, monkeypatch):
    from routers import collection_v2 as router

    submit_mock = AsyncMock(
        return_value=SimpleNamespace(
            job_id="job-123",
            status="accepted",
            message="Collection job started",
            estimated_time=5,
            webhook_url="/api/v2/jobs/job-123",
        )
    )
    monkeypatch.setattr(
        router.collection_module.jobs,
        "submit_batch_collect",
        submit_mock,
    )

    response = await authenticated_client.post(
        "/api/v2/collection/async",
        json={"date": "20240719", "meet": 1, "race_numbers": [1, 2]},
    )

    assert response.status_code == 202
    assert response.json()["job_id"] == "job-123"
    submit_mock.assert_awaited_once()
