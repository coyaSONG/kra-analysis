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
from services.job_contract import apply_job_shadow_fields
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
    result_payload: dict[str, Any] | None = None,
) -> None:
    """Update the Job record in the database."""
    async with async_session_maker() as db:
        try:
            query_result = await db.execute(select(Job).where(Job.job_id == job_id))
            job = query_result.scalar_one_or_none()

            if job:
                job.status = status
                apply_job_shadow_fields(job, lifecycle_status=status)
                if error:
                    job.error_message = error
                if result_payload is not None:
                    job.result = result_payload
                if task_id and hasattr(Job, "task_id"):
                    job.task_id = task_id
                if status in {"completed", "failed", "cancelled"}:
                    job.completed_at = datetime.now(UTC)
                await db.commit()
        except Exception as e:
            logger.error("Failed to update job status", job_id=job_id, error=str(e))


async def unsupported_job_type(
    job_kind: str, job_id: str | None = None
) -> dict[str, Any]:
    """Fail unsupported legacy job kinds without crashing the dispatcher."""
    payload = {
        "status": "failed",
        "job_kind": job_kind,
        "error": f"Unsupported job type: {job_kind}",
    }
    if job_id:
        await _add_job_log(
            job_id,
            "error",
            f"Unsupported job type: {job_kind}",
            {"job_kind": job_kind},
        )
        await _update_job_status(job_id, "failed", error=payload["error"])
    return payload


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
    manage_job_status: bool = True,
) -> dict[str, Any]:
    """Collect basic race data for a single race."""
    kra_api: KRAAPIService | None = None
    async with async_session_maker() as db:
        try:
            if job_id and manage_job_status:
                await _update_job_status(job_id, "processing", task_id=task_id)

            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)

            result = await collection_service.collect_race_data(
                race_date, meet, race_no, db
            )

            payload = {
                "status": "success",
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "data": result,
            }

            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully collected race {race_no}",
                    {"race_no": race_no},
                )

            if job_id and manage_job_status:
                await _update_job_status(
                    job_id,
                    "completed",
                    task_id=task_id,
                    result_payload=payload,
                )

            return payload

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
                if manage_job_status:
                    await _update_job_status(
                        job_id,
                        "failed",
                        error=str(e),
                        task_id=task_id,
                    )
            raise
        finally:
            if kra_api is not None:
                await kra_api.close()


# ---------------------------------------------------------------------------
# Task: preprocess race data
# ---------------------------------------------------------------------------


async def preprocess_race_data(
    race_id: str,
    job_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Preprocess previously collected race data."""
    kra_api: KRAAPIService | None = None
    async with async_session_maker() as db:
        try:
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)

            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)

            result = await collection_service.preprocess_race_data(race_id, db)

            payload = {"status": "success", "race_id": race_id, "data": result}

            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully preprocessed race {race_id}",
                    {"race_id": race_id},
                )

                await _update_job_status(
                    job_id, "completed", task_id=task_id, result_payload=payload
                )

            return payload

        except Exception as e:
            logger.error("Async preprocessing failed", race_id=race_id, error=str(e))
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to preprocess race {race_id}: {str(e)}",
                    {"race_id": race_id, "error": str(e)},
                )
                await _update_job_status(
                    job_id, "failed", error=str(e), task_id=task_id
                )
            raise
        finally:
            if kra_api is not None:
                await kra_api.close()


# ---------------------------------------------------------------------------
# Task: enrich race data
# ---------------------------------------------------------------------------


async def enrich_race_data(
    race_id: str,
    job_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Enrich previously collected race data."""
    kra_api: KRAAPIService | None = None
    async with async_session_maker() as db:
        try:
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)

            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)

            result = await collection_service.enrich_race_data(race_id, db)

            payload = {"status": "success", "race_id": race_id, "data": result}

            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully enriched race {race_id}",
                    {"race_id": race_id},
                )

                await _update_job_status(
                    job_id, "completed", task_id=task_id, result_payload=payload
                )

            return payload

        except Exception as e:
            logger.error("Async enrichment failed", race_id=race_id, error=str(e))
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to enrich race {race_id}: {str(e)}",
                    {"race_id": race_id, "error": str(e)},
                )
                await _update_job_status(
                    job_id, "failed", error=str(e), task_id=task_id
                )
            raise
        finally:
            if kra_api is not None:
                await kra_api.close()


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

    if job_id:
        await _update_job_status(job_id, "processing", task_id=task_id)

    for race_no in race_numbers:
        try:
            result = await collect_race_data(
                race_date,
                meet,
                race_no,
                job_id,
                task_id,
                manage_job_status=False,
            )
            results.append(result)
        except Exception as e:
            logger.error("Batch item failed", race_no=race_no, error=str(e))
            errors.append({"race_no": race_no, "error": str(e)})

    payload = {
        "status": "completed" if not errors else "partial",
        "race_date": race_date,
        "meet": meet,
        "results": results,
        "errors": errors,
    }

    if job_id:
        await _update_job_status(
            job_id,
            "completed" if not errors else "failed",
            error=f"{len(errors)} races failed during batch collection"
            if errors
            else None,
            task_id=task_id,
            result_payload=payload,
        )

    return payload


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
    kra_api: KRAAPIService | None = KRAAPIService()
    async with async_session_maker() as db:
        try:
            collection_service = CollectionService(kra_api)

            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)

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
                        Race.date == race_date,
                        Race.meet == meet,
                        Race.race_number == race_no,
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
            payload = {
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

            if job_id:
                await _update_job_status(
                    job_id, "completed", task_id=task_id, result_payload=payload
                )
                await _add_job_log(
                    job_id,
                    "info",
                    "Pipeline completed successfully",
                    {"race_id": race_id},
                )

            return payload

        except Exception as e:
            logger.error("Full pipeline async failed", error=str(e))
            if job_id:
                await _update_job_status(
                    job_id, "failed", error=str(e), task_id=task_id
                )
                await _add_job_log(
                    job_id, "error", f"Pipeline failed: {str(e)}", {"error": str(e)}
                )
            raise
        finally:
            if kra_api is not None:
                await kra_api.close()
