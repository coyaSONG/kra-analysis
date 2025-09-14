from datetime import datetime, timedelta

import pytest

from models.database_models import Job, JobStatus, JobType
from services.job_service import JobService


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

    class StubResult:
        def __init__(self):
            self.id = "stub-task-id"

    async def fake_dispatch(_self, _job):
        return StubResult()

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


@pytest.mark.asyncio
async def test_get_job_status_with_celery(monkeypatch, db_session):
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

    class DummyAsyncResult:
        def __init__(self, *_args, **_kwargs):
            self._state = "SUCCESS"
            self._info = {"ok": True}

        @property
        def state(self):
            return self._state

        @property
        def info(self):
            return self._info

        def ready(self):
            return True

        def successful(self):
            return True

    # Patch where AsyncResult is referenced in the service module
    import services.job_service as js

    monkeypatch.setattr(js, "AsyncResult", DummyAsyncResult)

    status = await service.get_job_status(job.job_id, db_session)
    assert status["celery_status"]["state"] == "SUCCESS"
    assert status["celery_status"]["successful"] is True


@pytest.mark.asyncio
async def test_cancel_job_revokes_task(monkeypatch, db_session):
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

    calls = {"revoked": []}

    from infrastructure import celery_app as cap

    def fake_revoke(task_id, terminate=False):
        calls["revoked"].append((task_id, terminate))

    monkeypatch.setattr(cap.celery_app.control, "revoke", fake_revoke)

    ok = await service.cancel_job(job.job_id, db_session)
    assert ok is True
    assert calls["revoked"][0] == ("to-cancel", True)


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
