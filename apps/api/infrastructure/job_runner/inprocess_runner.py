"""In-process job runner backed by infrastructure.background_tasks."""

from typing import Any

from infrastructure.background_tasks import cancel_task, get_task_status, submit_task
from infrastructure.job_runner.base import JobRunner
from models.database_models import Job


class InProcessJobRunner(JobRunner):
    """Default runner that executes tasks in the local asyncio process."""

    def submit(self, job: Job) -> str:
        from tasks.async_tasks import (
            batch_collect,
            collect_race_data,
            enrich_race_data,
            full_pipeline,
            preprocess_race_data,
        )

        params: dict[str, Any] = job.parameters or {}
        job_type = job.type.value if hasattr(job.type, "value") else str(job.type)

        if job_type == "collect_race":
            return submit_task(
                collect_race_data,
                params["race_date"],
                params["meet"],
                params["race_no"],
                job.job_id,
            )
        if job_type == "preprocess_race":
            return submit_task(
                preprocess_race_data,
                params["race_id"],
                job.job_id,
            )
        if job_type == "enrich_race":
            return submit_task(
                enrich_race_data,
                params["race_id"],
                job.job_id,
            )
        if job_type in ("batch_collect", "batch"):
            return submit_task(
                batch_collect,
                params["race_date"],
                params["meet"],
                params["race_numbers"],
                job.job_id,
            )
        if job_type == "full_pipeline":
            return submit_task(
                full_pipeline,
                params["race_date"],
                params["meet"],
                params["race_no"],
                job.job_id,
            )

        raise ValueError(f"Unknown job type: {job_type}")

    async def status(self, task_id: str) -> dict[str, Any] | None:
        return await get_task_status(task_id)

    async def cancel(self, task_id: str) -> bool:
        return await cancel_task(task_id)
