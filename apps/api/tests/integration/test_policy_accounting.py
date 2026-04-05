import pytest
from sqlalchemy import select

from models.database_models import Job, JobStatus, JobType, UsageEvent


@pytest.mark.asyncio
async def test_jobs_list_persists_usage_event(authenticated_client, db_session):
    response = await authenticated_client.get("/api/v2/jobs/")

    assert response.status_code == 200
    events = (await db_session.execute(select(UsageEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].action == "jobs.list"
    assert events[0].owner_ref == "test-api-key-123"
    assert events[0].status_code == 200
    assert events[0].outcome == "success"
    assert events[0].path == "/api/v2/jobs/"


@pytest.mark.asyncio
async def test_jobs_read_persists_usage_event(authenticated_client, db_session):
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.PENDING,
        parameters={},
        created_by="test-api-key-123",
    )
    db_session.add(job)
    await db_session.commit()

    response = await authenticated_client.get(f"/api/v2/jobs/{job.job_id}")

    assert response.status_code == 200
    events = (
        (
            await db_session.execute(
                select(UsageEvent).order_by(
                    UsageEvent.created_at.desc(), UsageEvent.id.desc()
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].action == "jobs.read"
    assert events[0].status_code == 200
    assert events[0].path == f"/api/v2/jobs/{job.job_id}"
