import pytest

from infrastructure.job_runner import reset_job_runner_cache
from infrastructure.job_runner.celery_runner import CeleryJobRunner
from services.job_service import JobService
from tasks.celery_app import get_celery_app, reset_celery_app_cache


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_service_celery_mode_eager_roundtrip(monkeypatch, db_session):
    pytest.importorskip("celery")

    import config

    monkeypatch.setattr(config.settings, "job_runner_mode", "celery")
    monkeypatch.setattr(config.settings, "celery_broker_url", "memory://")
    monkeypatch.setattr(config.settings, "celery_result_backend", "cache+memory://")
    monkeypatch.setattr(config.settings, "celery_task_always_eager", True)
    monkeypatch.setattr(config.settings, "celery_task_eager_propagates", True)
    monkeypatch.setattr(config.settings, "celery_task_store_eager_result", True)

    reset_celery_app_cache()
    reset_job_runner_cache()
    celery_app = get_celery_app()

    @celery_app.task(name="kra.batch_collect", bind=True)
    def _stub_batch_collect(self, race_date, meet, race_numbers, job_id=None):
        return {
            "status": "completed",
            "race_date": race_date,
            "meet": meet,
            "race_numbers": race_numbers,
            "job_id": job_id,
            "task_id": self.request.id,
        }

    service = JobService(job_runner=CeleryJobRunner(celery_app=celery_app))

    job = await service.create_job(
        job_type="batch",
        parameters={"race_date": "20240719", "meet": 1, "race_numbers": [1, 2]},
        user_id="tester",
        db=db_session,
    )

    task_id = await service.start_job(str(job.job_id), db_session)
    status = await service.get_job_status(str(job.job_id), db_session)

    assert task_id
    assert status["status"] == "queued"
    assert status["task_status"] is not None
    assert status["task_status"]["task_id"] == task_id
    assert status["task_status"]["state"] in {"success", "completed"}
    assert status["task_status"]["result"]["status"] == "completed"
