from unittest.mock import AsyncMock, Mock

import pytest

from services.collection_workflow import CollectionWorkflow


def test_build_batch_plan_defaults_to_full_field():
    from models.collection_dto import CollectionRequest

    request = CollectionRequest(date="20240719", meet=1, race_numbers=None)
    plan = CollectionWorkflow.build_batch_plan(request)

    assert plan.race_date == "20240719"
    assert plan.meet == 1
    assert plan.race_numbers == list(range(1, 16))


@pytest.mark.asyncio
async def test_collect_batch_centralizes_partial_failure(monkeypatch):
    workflow = CollectionWorkflow()

    class FakeCollectionService:
        def __init__(self, kra_api):
            self.kra_api = kra_api

        async def collect_race_data(self, race_date, meet, race_no, db):
            if race_no == 2:
                raise RuntimeError("boom")
            return {"race_no": race_no}

    monkeypatch.setattr(
        "services.collection_workflow.CollectionService", FakeCollectionService
    )

    plan = CollectionWorkflow.build_batch_plan_from_values(
        "20240719", 1, [1, 2, 3]
    )
    outcome = await workflow.collect_batch(plan, Mock(), Mock())

    assert outcome.status == "partial"
    assert [item["race_no"] for item in outcome.results] == [1, 3]
    assert outcome.errors == [{"race_no": 2, "error": "boom"}]


@pytest.mark.asyncio
async def test_submit_batch_job_uses_job_service():
    workflow = CollectionWorkflow()
    workflow.job_service.create_job = AsyncMock(
        return_value=Mock(job_id="job-123")
    )
    workflow.job_service.start_job = AsyncMock(return_value="task-123")

    plan = CollectionWorkflow.build_batch_plan_from_values("20240719", 1, [1, 2])
    db = Mock()
    response = await workflow.submit_batch_job(
        plan,
        owner_ref="owner-1",
        db=db,
    )

    assert response.job_id == "job-123"
    assert response.status == "accepted"
    workflow.job_service.create_job.assert_awaited_once()
    workflow.job_service.start_job.assert_awaited_once_with("job-123", db)
