"""Celery-backed job runner implementation."""

from datetime import UTC, datetime
from typing import Any

from infrastructure.job_runner.base import JobRunner
from models.database_models import Job
from tasks.celery_app import get_celery_app


class CeleryJobRunner(JobRunner):
    """Background runner that dispatches jobs to Celery."""

    TASK_NAME_BY_TYPE = {
        "collect_race": "kra.collect_race_data",
        "preprocess_race": "kra.preprocess_race_data",
        "enrich_race": "kra.enrich_race_data",
        "batch_collect": "kra.batch_collect",
        "batch": "kra.batch_collect",
        "full_pipeline": "kra.full_pipeline",
    }

    def __init__(self, celery_app=None):
        self.celery_app = celery_app or get_celery_app()

    @staticmethod
    def _job_type(job: Job) -> str:
        return job.type.value if hasattr(job.type, "value") else str(job.type)

    @staticmethod
    def _job_id(job: Job) -> str:
        return str(job.job_id)

    def _build_kwargs(
        self, job_type: str, params: dict[str, Any], job_id: str
    ) -> dict[str, Any]:
        if job_type == "collect_race":
            return {
                "race_date": params["race_date"],
                "meet": params["meet"],
                "race_no": params["race_no"],
                "job_id": job_id,
            }
        if job_type == "preprocess_race":
            return {"race_id": params["race_id"], "job_id": job_id}
        if job_type == "enrich_race":
            return {"race_id": params["race_id"], "job_id": job_id}
        if job_type in ("batch_collect", "batch"):
            return {
                "race_date": params["race_date"],
                "meet": params["meet"],
                "race_numbers": params["race_numbers"],
                "job_id": job_id,
            }
        if job_type == "full_pipeline":
            return {
                "race_date": params["race_date"],
                "meet": params["meet"],
                "race_no": params["race_no"],
                "job_id": job_id,
            }
        raise ValueError(f"Unknown job type: {job_type}")

    def submit(self, job: Job) -> str:
        params: dict[str, Any] = job.parameters or {}
        job_type = self._job_type(job)
        task_name = self.TASK_NAME_BY_TYPE.get(job_type)
        if task_name is None:
            raise ValueError(f"Unknown job type: {job_type}")

        task = self.celery_app.tasks.get(task_name)
        if task is None:
            # Ensure task registry is loaded from declared imports.
            self.celery_app.loader.import_default_modules()
            task = self.celery_app.tasks.get(task_name)
            if task is None:
                raise RuntimeError(f"Celery task not registered: {task_name}")

        task_kwargs = self._build_kwargs(job_type, params, self._job_id(job))
        async_result = task.apply_async(kwargs=task_kwargs)
        return async_result.id

    async def status(self, task_id: str) -> dict[str, Any] | None:
        result = self.celery_app.AsyncResult(task_id)
        if result is None:
            return None

        payload: dict[str, Any] = {
            "task_id": task_id,
            "state": result.state.lower(),
            "alive": not result.ready(),
            "updated_at": datetime.now(UTC).isoformat(),
            "result": None,
            "error": None,
        }

        if result.successful():
            payload["result"] = result.result
        elif result.failed():
            payload["error"] = str(result.result)
        elif result.state.upper() in {"REVOKED"}:
            payload["error"] = "revoked"

        return payload

    async def cancel(self, task_id: str) -> bool:
        result = self.celery_app.AsyncResult(task_id)
        if result.ready():
            return False
        result.revoke(terminate=True)
        return True

    def health(self) -> dict[str, int | str]:
        """Celery worker/broker liveness for detailed health endpoint."""
        try:
            ping_result = self.celery_app.control.inspect(timeout=1.0).ping()
            worker_count = len(ping_result or {})
            if worker_count == 0:
                return {
                    "status": "degraded",
                    "tracked": 0,
                    "running": 0,
                    "failed": 1,
                    "cancelled": 0,
                }
            return {
                "status": "healthy",
                "tracked": worker_count,
                "running": worker_count,
                "failed": 0,
                "cancelled": 0,
            }
        except Exception:
            return {
                "status": "degraded",
                "tracked": 0,
                "running": 0,
                "failed": 1,
                "cancelled": 0,
            }
