"""
Async background tasks for data collection.
Pure async functions that replace the former Celery task wrappers.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, select

from infrastructure.database import async_session_maker
from models.database_models import Job, JobLog, Race
from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Helper: DB helpers (shared across tasks)
# ---------------------------------------------------------------------------


async def _update_job_status(
    job_id: str,
    status: str,
    error: str | None = None,
    task_id: str | None = None,
) -> None:
    """Update the Job record in the database."""
    async with async_session_maker() as db:
        try:
            result = await db.execute(select(Job).where(Job.job_id == job_id))
            job = result.scalar_one_or_none()

            if job:
                job.status = status  # type: ignore[assignment]

                if error:
                    job.error_message = error  # type: ignore[assignment]
                if task_id and hasattr(Job, "task_id"):
                    job.task_id = task_id
                if status == "completed":
                    job.completed_at = datetime.now(UTC)  # type: ignore[assignment]

                await db.commit()
        except Exception as e:
            logger.error("Failed to update job status", job_id=job_id, error=str(e))


async def _add_job_log(
    job_id: str,
    level: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Append a log entry for the given Job."""
    async with async_session_maker() as db:
        try:
            log = JobLog(
                job_id=job_id,
                level=level,
                message=message,
                log_metadata=data or {},
            )
            db.add(log)
            await db.commit()
        except Exception as e:
            logger.error("Failed to add job log", job_id=job_id, error=str(e))


# ---------------------------------------------------------------------------
# Task: collect race data
# ---------------------------------------------------------------------------


async def collect_race_data(
    race_date: str,
    meet: int,
    race_no: int,
    job_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Collect basic race data for a single race."""
    async with async_session_maker() as db:
        try:
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)

            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)

            result = await collection_service.collect_race_data(
                race_date, meet, race_no, db
            )

            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully collected race {race_no}",
                    {"race_no": race_no},
                )

            await kra_api.close()

            return {
                "status": "success",
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "data": result,
            }

        except Exception as e:
            logger.error(
                "Async collection failed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                error=str(e),
            )
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to collect race {race_no}: {str(e)}",
                    {"race_no": race_no, "error": str(e)},
                )
            raise


# ---------------------------------------------------------------------------
# Task: preprocess race data
# ---------------------------------------------------------------------------


async def preprocess_race_data(
    race_id: str,
    job_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Preprocess previously collected race data."""
    async with async_session_maker() as db:
        try:
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)

            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)

            result = await collection_service.preprocess_race_data(race_id, db)

            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully preprocessed race {race_id}",
                    {"race_id": race_id},
                )

            await kra_api.close()
            return {"status": "success", "race_id": race_id, "data": result}

        except Exception as e:
            logger.error("Async preprocessing failed", race_id=race_id, error=str(e))
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to preprocess race {race_id}: {str(e)}",
                    {"race_id": race_id, "error": str(e)},
                )
            raise


# ---------------------------------------------------------------------------
# Task: enrich race data
# ---------------------------------------------------------------------------


async def enrich_race_data(
    race_id: str,
    job_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Enrich previously collected race data."""
    async with async_session_maker() as db:
        try:
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)

            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)

            result = await collection_service.enrich_race_data(race_id, db)

            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully enriched race {race_id}",
                    {"race_id": race_id},
                )

            await kra_api.close()
            return {"status": "success", "race_id": race_id, "data": result}

        except Exception as e:
            logger.error("Async enrichment failed", race_id=race_id, error=str(e))
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to enrich race {race_id}: {str(e)}",
                    {"race_id": race_id, "error": str(e)},
                )
            raise


# ---------------------------------------------------------------------------
# Task: batch collect
# ---------------------------------------------------------------------------


async def batch_collect(
    race_date: str,
    meet: int,
    race_numbers: list[int],
    job_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Collect data for multiple races sequentially."""
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for race_no in race_numbers:
        try:
            result = await collect_race_data(race_date, meet, race_no, job_id, task_id)
            results.append(result)
        except Exception as e:
            logger.error("Batch item failed", race_no=race_no, error=str(e))
            errors.append({"race_no": race_no, "error": str(e)})

    return {
        "status": "completed" if not errors else "partial",
        "race_date": race_date,
        "meet": meet,
        "results": results,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Task: full pipeline (collect -> preprocess -> enrich)
# ---------------------------------------------------------------------------


async def full_pipeline(
    race_date: str,
    meet: int,
    race_no: int,
    job_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Run the complete collection pipeline: collect -> preprocess -> enrich."""
    async with async_session_maker() as db:
        try:
            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)

            # 1. Collect
            if job_id:
                await _add_job_log(
                    job_id, "info", "Starting data collection", {"step": "collect"}
                )

            await collection_service.collect_race_data(race_date, meet, race_no, db)

            # Find the race_id
            result = await db.execute(
                select(Race).where(
                    and_(
                        Race.race_date == race_date,  # type: ignore[arg-type]
                        Race.meet == meet,
                        Race.race_no == race_no,  # type: ignore[arg-type]
                    )
                )
            )
            race = result.scalar_one_or_none()
            if not race:
                raise ValueError("Race not found after collection")

            race_id = race.id

            # 2. Preprocess
            if job_id:
                await _add_job_log(
                    job_id, "info", "Starting preprocessing", {"step": "preprocess"}
                )

            await collection_service.preprocess_race_data(race_id, db)

            # 3. Enrich
            if job_id:
                await _add_job_log(
                    job_id, "info", "Starting enrichment", {"step": "enrich"}
                )

            await collection_service.enrich_race_data(race_id, db)

            # Done
            if job_id:
                await _update_job_status(job_id, "completed")
                await _add_job_log(
                    job_id,
                    "info",
                    "Pipeline completed successfully",
                    {"race_id": race_id},
                )

            await kra_api.close()

            return {
                "status": "success",
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "race_id": race_id,
                "steps": {
                    "collect": "completed",
                    "preprocess": "completed",
                    "enrich": "completed",
                },
            }

        except Exception as e:
            logger.error("Full pipeline async failed", error=str(e))
            if job_id:
                await _add_job_log(
                    job_id, "error", f"Pipeline failed: {str(e)}", {"error": str(e)}
                )
            raise
