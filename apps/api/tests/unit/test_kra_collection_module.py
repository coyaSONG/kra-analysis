from unittest.mock import AsyncMock, Mock

import pytest

from services.kra_collection_module import (
    BatchCollectInput,
    CollectionCommands,
    CollectionJobs,
    CollectionQueries,
)


@pytest.mark.asyncio
async def test_collection_commands_collect_batch_returns_partial(monkeypatch):
    async def fake_get_kra_api_service():
        return Mock(name="kra_api")

    class FakeWorkflow:
        async def collect(self, cmd):
            if cmd.key.race_number == 2:
                raise RuntimeError("boom")
            return Mock(payload={"race_no": cmd.key.race_number})

    monkeypatch.setattr(
        "services.kra_collection_module.get_kra_api_service",
        fake_get_kra_api_service,
    )

    commands = CollectionCommands()
    monkeypatch.setattr(commands, "_build_workflow", lambda kra_api, db: FakeWorkflow())
    outcome = await commands.collect_batch(
        BatchCollectInput(race_date="20240719", meet=1, race_numbers=[1, 2, 3]),
        db=Mock(),
    )

    assert outcome.status == "partial"
    assert [item["race_no"] for item in outcome.data] == [1, 3]
    assert outcome.errors == [{"race_no": 2, "error": "boom"}]


@pytest.mark.asyncio
async def test_collection_jobs_submit_batch_collect_defaults_race_numbers():
    job_service = Mock()
    job_service.create_job = AsyncMock(return_value=Mock(job_id="job-123"))
    job_service.start_job = AsyncMock(return_value="task-123")
    db = Mock()

    jobs = CollectionJobs(job_service=job_service)
    receipt = await jobs.submit_batch_collect(
        BatchCollectInput(race_date="20240719", meet=1, race_numbers=None),
        owner_ref="owner-1",
        db=db,
    )

    assert receipt.job_id == "job-123"
    assert receipt.status == "accepted"
    job_service.create_job.assert_awaited_once_with(
        job_type="batch",
        parameters={
            "race_date": "20240719",
            "meet": 1,
            "race_numbers": list(range(1, 16)),
        },
        owner_ref="owner-1",
        db=db,
    )
    job_service.start_job.assert_awaited_once_with("job-123", db)


@pytest.mark.asyncio
async def test_collection_queries_wrap_collection_status(monkeypatch):
    monkeypatch.setattr(
        "services.kra_collection_module.CollectionService.get_collection_status",
        AsyncMock(
            return_value={
                "date": "20240719",
                "meet": 1,
                "total_races": 10,
                "collected_races": 8,
                "enriched_races": 5,
                "status": "running",
                "collection_status": "collected",
                "enrichment_status": "enriched",
                "result_status": "pending",
                "last_updated": None,
            }
        ),
    )

    queries = CollectionQueries()
    snapshot = await queries.get_status(race_date="20240719", meet=1, db=Mock())

    assert snapshot.date == "20240719"
    assert snapshot.meet == 1
    assert snapshot.status == "running"
