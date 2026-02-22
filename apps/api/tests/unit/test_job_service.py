from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from models.database_models import Job, JobStatus, JobType
from services.job_service import JobService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_job(db_session):
    service = JobService()
    params = {"race_date": "20240719", "meet": 1, "race_numbers": [1]}
    job = await service.create_job(
        job_type=JobType.COLLECTION.value,  # use enum value to satisfy DB enum
        parameters=params,
        user_id="tester",
        db=db_session,
    )
    assert job.job_id
    assert job.parameters["meet"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_job_queues_task(db_session):
    runner = Mock()
    runner.submit.return_value = "stub-task-id"
    service = JobService(job_runner=runner)
    # prepare job
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.PENDING,
        parameters={"race_date": "20240719", "meet": 1, "race_numbers": [1]},
        created_by="tester",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    task_id = await service.start_job(job.job_id, db_session)
    assert task_id == "stub-task-id"
    runner.submit.assert_called_once()

    # reload
    job2 = await service.get_job(job.job_id, db_session)
    assert str(job2.status.value if hasattr(job2.status, "value") else job2.status) in (
        "queued",
        JobStatus.QUEUED.value,
    )
    assert job2.task_id == "stub-task-id"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_status_with_task(db_session):
    runner = Mock()
    service = JobService(job_runner=runner)
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.PROCESSING,
        parameters={},
        created_by="tester",
    )
    # preset task id
    job.task_id = "task-123"
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    fake_status = {
        "task_id": "task-123",
        "state": "completed",
        "result": {"ok": True},
        "error": None,
        "alive": False,
    }

    runner.status = AsyncMock(return_value=fake_status)

    status = await service.get_job_status(job.job_id, db_session)
    assert status["task_status"]["state"] == "completed"
    runner.status.assert_awaited_once_with("task-123")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_job_cancels_task(db_session):
    runner = Mock()
    runner.cancel = AsyncMock(return_value=True)
    service = JobService(job_runner=runner)
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.RUNNING,
        parameters={},
        created_by="tester",
    )
    job.task_id = "to-cancel"
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    ok = await service.cancel_job(job.job_id, db_session)
    assert ok is True
    runner.cancel.assert_awaited_once_with("to-cancel")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_old_jobs(db_session):
    service = JobService()
    old_date = datetime.now(UTC) - timedelta(days=10)

    # create two old completed jobs and one recent
    j1 = Job(
        type=JobType.COLLECTION,
        status=JobStatus.COMPLETED,
        parameters={},
        created_by="t",
        created_at=old_date,
    )
    j2 = Job(
        type=JobType.COLLECTION,
        status=JobStatus.FAILED,
        parameters={},
        created_by="t",
        created_at=old_date,
    )
    j3 = Job(
        type=JobType.COLLECTION, status=JobStatus.PENDING, parameters={}, created_by="t"
    )
    db_session.add_all([j1, j2, j3])
    await db_session.commit()
    await db_session.refresh(j3)

    deleted = await service.cleanup_old_jobs(db_session, days=7)
    assert deleted >= 2
    pending_job = await service.get_job(j3.job_id, db_session)
    assert pending_job is not None
    assert (
        str(
            pending_job.status.value
            if hasattr(pending_job.status, "value")
            else pending_job.status
        )
        == JobStatus.PENDING.value
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_collect_race():
    runner = Mock()
    runner.submit.return_value = "task-id"
    service = JobService(job_runner=runner)
    job = SimpleNamespace(
        type="collect_race",
        parameters={"race_date": "20240719", "meet": 1, "race_no": 3},
        job_id="job-1",
    )

    result = await service._dispatch_task(job)

    assert result == "task-id"
    runner.submit.assert_called_once_with(job)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_unknown_type():
    runner = Mock()
    runner.submit.side_effect = ValueError("Unknown job type: unknown")
    service = JobService(job_runner=runner)

    job = SimpleNamespace(type="unknown", parameters={}, job_id="job-1")

    with pytest.raises(ValueError):
        await service._dispatch_task(job)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_status_missing_returns_none(db_session):
    service = JobService()
    assert await service.get_job_status("missing", db_session) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_jobs_with_total_returns_paginated_jobs_and_total(db_session):
    service = JobService()

    jobs = [
        Job(
            type=JobType.COLLECTION,
            status=JobStatus.COMPLETED,
            parameters={"idx": 1},
            created_by="tester",
        ),
        Job(
            type=JobType.COLLECTION,
            status=JobStatus.COMPLETED,
            parameters={"idx": 2},
            created_by="tester",
        ),
        Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={"idx": 3},
            created_by="tester",
        ),
    ]
    db_session.add_all(jobs)
    await db_session.commit()

    paged_jobs, total = await service.list_jobs_with_total(
        db=db_session, status="completed", limit=1, offset=0
    )

    assert len(paged_jobs) == 1
    assert total == 2


@pytest.mark.unit
def test_calculate_progress_full_pipeline_steps():
    service = JobService()
    job = SimpleNamespace(status="processing", type="full_pipeline")
    task_status = {
        "result": {
            "steps": {
                "collect": "completed",
                "enrich": "completed",
                "finalize": "pending",
            }
        }
    }

    assert service._calculate_progress(job, task_status) == 10 + 2 * 30


@pytest.mark.unit
def test_job_service_methods_exist():
    """Test that JobService exposes expected public contract methods."""
    service = JobService()

    expected_public_methods = [
        "create_job",
        "start_job",
        "get_job",
        "get_job_status",
        "get_job_logs",
        "add_job_log",
        "list_jobs",
        "list_jobs_with_total",
        "cancel_job",
        "cleanup_old_jobs",
        "get_job_statistics",
    ]

    missing = [
        method for method in expected_public_methods if not hasattr(service, method)
    ]
    assert missing == []
    assert all(callable(getattr(service, method)) for method in expected_public_methods)
