from types import SimpleNamespace

import pytest

import services.job_service as job_service_module
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

    original_celery_app = job_service_module.celery_app
    job_service_module.celery_app = SimpleNamespace(
        control=SimpleNamespace(revoke=lambda *_args, **_kwargs: None)
    )

    try:
        response = await authenticated_client.post(f"/api/v2/jobs/{job.job_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["message"]
    finally:
        job_service_module.celery_app = original_celery_app

    updated = await job_service_module.JobService().get_job(str(job.job_id), db_session)
    assert str(updated.status) in ("cancelled", JobStatus.CANCELLED.value)
