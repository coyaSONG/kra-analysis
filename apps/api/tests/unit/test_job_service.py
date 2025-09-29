from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

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


@pytest.mark.unit
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


@pytest.mark.unit
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
def test_get_celery_components_prefers_injected(monkeypatch):
    import services.job_service as js

    dummy_app = object()
    dummy_async_result = object()

    original_app = js.celery_app
    original_async_result = js.AsyncResult

    js.celery_app = dummy_app
    js.AsyncResult = dummy_async_result

    try:
        app, async_result = JobService._get_celery_components()
        assert app is dummy_app
        assert async_result is dummy_async_result
    finally:
        js.celery_app = original_app
        js.AsyncResult = original_async_result


@pytest.mark.unit
def test_get_celery_components_handles_missing(monkeypatch):
    import services.job_service as js

    original_app = js.celery_app
    original_async_result = js.AsyncResult

    js.celery_app = None
    js.AsyncResult = None

    def fake_import(name: str):
        raise ImportError(f"missing {name}")

    monkeypatch.setattr(js.importlib, "import_module", fake_import)

    try:
        app, async_result = JobService._get_celery_components()
        assert app is None
        assert async_result is None
    finally:
        js.celery_app = original_app
        js.AsyncResult = original_async_result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_collect_race(monkeypatch):
    service = JobService()

    class DummyTask:
        def __init__(self):
            self.calls: list[tuple[Any, ...]] = []

        def delay(self, *args: Any):
            self.calls.append(args)
            return SimpleNamespace(id="task-id")

    task = DummyTask()

    tasks_module = SimpleNamespace(
        collect_race_data_task=task,
        preprocess_race_data_task=task,
        enrich_race_data_task=task,
        batch_collect_races_task=task,
        full_pipeline_task=task,
    )

    monkeypatch.setattr(
        JobService, "_get_collection_tasks_module", lambda _self: tasks_module
    )
    monkeypatch.setattr(
        JobService, "_get_celery_components", lambda _self: (object(), object())
    )

    job = SimpleNamespace(
        type="collect_race",
        parameters={"race_date": "20240719", "meet": 1, "race_no": 3},
        job_id="job-1",
    )

    result = await service._dispatch_task(job)

    assert task.calls[0] == ("20240719", 1, 3, "job-1")
    assert result.id == "task-id"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_requires_celery(monkeypatch):
    service = JobService()
    job = SimpleNamespace(type="collect_race", parameters={}, job_id="job-1")

    monkeypatch.setattr(JobService, "_get_collection_tasks_module", lambda _self: None)
    monkeypatch.setattr(
        JobService, "_get_celery_components", lambda _self: (None, None)
    )

    with pytest.raises(RuntimeError):
        await service._dispatch_task(job)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_unknown_type(monkeypatch):
    service = JobService()

    class DummyTask:
        def delay(self, *args: Any):
            return SimpleNamespace(id="task-id")

    tasks_module = SimpleNamespace(
        collect_race_data_task=DummyTask(),
        preprocess_race_data_task=DummyTask(),
        enrich_race_data_task=DummyTask(),
        batch_collect_races_task=DummyTask(),
        full_pipeline_task=DummyTask(),
    )

    monkeypatch.setattr(
        JobService, "_get_collection_tasks_module", lambda _self: tasks_module
    )
    monkeypatch.setattr(
        JobService, "_get_celery_components", lambda _self: (object(), object())
    )

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
    celery_status = {
        "info": {
            "steps": {
                "collect": "completed",
                "enrich": "completed",
                "finalize": "pending",
            }
        }
    }

    assert service._calculate_progress(job, celery_status) == 10 + 2 * 30


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_collection_tasks_module_import_error(monkeypatch):
    """Test _get_collection_tasks_module when import fails"""
    service = JobService()

    import importlib

    def fake_import(name):
        raise ImportError("Module not found")

    monkeypatch.setattr(importlib, "import_module", fake_import)

    result = service._get_collection_tasks_module()
    assert result is None


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
    assert hasattr(service, "_get_celery_components")
    assert hasattr(service, "_get_collection_tasks_module")
