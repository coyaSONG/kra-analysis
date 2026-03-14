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
