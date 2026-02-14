from unittest.mock import AsyncMock, patch

import pytest

from models.database_models import Job, JobStatus, JobType


@pytest.mark.asyncio
async def test_jobs_v2_list_returns_jobs(authenticated_client, db_session):
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.PENDING,
        parameters={"race_date": "20240719"},
        created_by="tester",
    )
    db_session.add(job)
    await db_session.commit()

    response = await authenticated_client.get("/api/v2/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    job_ids = {item["job_id"] for item in data["jobs"]}
    assert str(job.job_id) in job_ids


@pytest.mark.asyncio
async def test_jobs_v2_get_detail_returns_logs(authenticated_client, db_session):
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.PROCESSING,
        parameters={"race_date": "20240719"},
        created_by="tester",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    response = await authenticated_client.get(f"/api/v2/jobs/{job.job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job"]["job_id"] == str(job.job_id)
    assert isinstance(data["logs"], list)


@pytest.mark.asyncio
async def test_jobs_v2_cancel_endpoint_updates_status(authenticated_client, db_session):
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.RUNNING,
        parameters={"race_date": "20240719"},
        created_by="tester",
    )
    job.task_id = "task-to-cancel"
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with patch(
        "services.job_service.cancel_task",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await authenticated_client.post(f"/api/v2/jobs/{job.job_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["message"]

    from services.job_service import JobService

    updated = await JobService().get_job(str(job.job_id), db_session)
    assert str(updated.status) in ("cancelled", JobStatus.CANCELLED.value)
