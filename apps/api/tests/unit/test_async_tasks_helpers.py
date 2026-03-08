from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from models.database_models import Job, JobLog, JobStatus, JobType
from tasks import async_tasks


@pytest.fixture
def patch_async_tasks_session_maker(monkeypatch, test_db_engine):
    session_maker = async_sessionmaker(
        test_db_engine,
        expire_on_commit=False,
    )
    monkeypatch.setattr(async_tasks, "async_session_maker", session_maker)
    return session_maker


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_job_status_uses_job_id_and_error_message(
    patch_async_tasks_session_maker,
):
    async with patch_async_tasks_session_maker() as session:
        job = Job(
            job_id="job-async-1",
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            created_by="tester",
            parameters={},
        )
        session.add(job)
        await session.commit()

    await async_tasks._update_job_status(
        job_id="job-async-1",
        status="completed",
        error="boom",
    )

    async with patch_async_tasks_session_maker() as session:
        row = await session.execute(select(Job).where(Job.job_id == "job-async-1"))
        updated = row.scalar_one()
        status_value = (
            updated.status.value
            if hasattr(updated.status, "value")
            else str(updated.status)
        )
        assert status_value == "completed"
        assert updated.error_message == "boom"
        assert updated.completed_at is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_add_job_log_uses_log_metadata_field(patch_async_tasks_session_maker):
    async with patch_async_tasks_session_maker() as session:
        job = Job(
            job_id="job-async-2",
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            created_by="tester",
            parameters={},
            created_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()

    await async_tasks._add_job_log(
        job_id="job-async-2",
        level="info",
        message="hello",
        data={"k": "v"},
    )

    async with patch_async_tasks_session_maker() as session:
        row = await session.execute(
            select(JobLog).where(JobLog.job_id == "job-async-2").limit(1)
        )
        log = row.scalar_one()
        assert log.level == "info"
        assert log.message == "hello"
        assert log.log_metadata == {"k": "v"}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_collect_race_data_marks_job_completed(
    patch_async_tasks_session_maker, monkeypatch
):
    async with patch_async_tasks_session_maker() as session:
        job = Job(
            job_id="job-async-3",
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            created_by="tester",
            parameters={},
        )
        session.add(job)
        await session.commit()

    class FakeKRA:
        async def close(self):
            return None

    class FakeCollectionService:
        def __init__(self, kra_api):
            self.kra_api = kra_api

        async def collect_race_data(self, race_date, meet, race_no, db):
            return {"race_date": race_date, "meet": meet, "race_no": race_no}

    monkeypatch.setattr(async_tasks, "KRAAPIService", FakeKRA)
    monkeypatch.setattr(async_tasks, "CollectionService", FakeCollectionService)

    await async_tasks.collect_race_data(
        "20240719", 1, 1, job_id="job-async-3", task_id="task-3"
    )

    async with patch_async_tasks_session_maker() as session:
        row = await session.execute(select(Job).where(Job.job_id == "job-async-3"))
        updated = row.scalar_one()
        assert updated.status == JobStatus.COMPLETED
        assert updated.result["race_no"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_batch_collect_marks_job_failed_on_partial_errors(
    patch_async_tasks_session_maker, monkeypatch
):
    async with patch_async_tasks_session_maker() as session:
        job = Job(
            job_id="job-async-4",
            type=JobType.BATCH,
            status=JobStatus.PENDING,
            created_by="tester",
            parameters={},
        )
        session.add(job)
        await session.commit()

    calls = {"count": 0}

    async def fake_collect_race_data(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"status": "success", "race_no": 1}
        raise RuntimeError("boom")

    monkeypatch.setattr(async_tasks, "collect_race_data", fake_collect_race_data)

    result = await async_tasks.batch_collect(
        "20240719", 1, [1, 2], job_id="job-async-4", task_id="task-4"
    )

    assert result["status"] == "partial"

    async with patch_async_tasks_session_maker() as session:
        row = await session.execute(select(Job).where(Job.job_id == "job-async-4"))
        updated = row.scalar_one()
        assert updated.status == JobStatus.FAILED
        assert updated.result["status"] == "partial"
