from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

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
async def test_start_job_queues_task(monkeypatch, db_session):
    service = JobService()
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

    async def fake_dispatch(_self, _job):
        return "stub-task-id"

    monkeypatch.setattr(JobService, "_dispatch_task", fake_dispatch)

    task_id = await service.start_job(job.job_id, db_session)
    assert task_id == "stub-task-id"

    # reload
    job2 = await service.get_job(job.job_id, db_session)
    assert str(job2.status.value if hasattr(job2.status, "value") else job2.status) in (
        "queued",
        JobStatus.QUEUED.value,
    )
    assert job2.task_id == "stub-task-id"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_status_with_task(monkeypatch, db_session):
    service = JobService()
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

    with patch(
        "services.job_service.get_task_status",
        new_callable=AsyncMock,
        return_value=fake_status,
    ):
        status = await service.get_job_status(job.job_id, db_session)
        assert status["task_status"]["state"] == "completed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_job_cancels_task(monkeypatch, db_session):
    service = JobService()
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

    with patch(
        "services.job_service.cancel_task",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_cancel:
        ok = await service.cancel_job(job.job_id, db_session)
        assert ok is True
        mock_cancel.assert_awaited_once_with("to-cancel")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_old_jobs(db_session):
    service = JobService()
    old_date = datetime.utcnow() - timedelta(days=10)

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

    deleted = await service.cleanup_old_jobs(db_session, days=7)
    assert deleted >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_collect_race(monkeypatch):
    service = JobService()

    with patch(
        "services.job_service.submit_task",
        return_value="task-id",
    ) as mock_submit:
        job = SimpleNamespace(
            type="collect_race",
            parameters={"race_date": "20240719", "meet": 1, "race_no": 3},
            job_id="job-1",
        )

        result = await service._dispatch_task(job)

        assert result == "task-id"
        assert mock_submit.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_unknown_type(monkeypatch):
    service = JobService()

    job = SimpleNamespace(type="unknown", parameters={}, job_id="job-1")

    with pytest.raises(ValueError):
        await service._dispatch_task(job)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_status_missing_returns_none(db_session):
    service = JobService()
    assert await service.get_job_status("missing", db_session) is None


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
    """Test that JobService has expected methods"""
    service = JobService()

    # Check that service has expected methods
    assert hasattr(service, "create_job")
    assert hasattr(service, "get_job")
    assert hasattr(service, "list_jobs")
    assert hasattr(service, "get_job_status")
    assert hasattr(service, "cancel_job")
    assert hasattr(service, "start_job")
    assert hasattr(service, "_calculate_progress")
    assert hasattr(service, "_dispatch_task")
