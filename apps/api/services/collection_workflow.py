"""
Collection orchestration workflow.

Centralizes batch request planning and partial-failure handling while keeping
CollectionService focused on per-race collection and persistence.
"""

from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.collection_dto import CollectionRequest, CollectionResponse
from services.collection_service import CollectionService
from services.job_service import JobService
from services.kra_api_service import KRAAPIService

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class BatchCollectionPlan:
    race_date: str
    meet: int
    race_numbers: list[int]


@dataclass(frozen=True, slots=True)
class BatchCollectionOutcome:
    status: str
    message: str
    results: list[dict[str, Any]]
    errors: list[dict[str, Any]]

    def to_response(self) -> CollectionResponse:
        return CollectionResponse(
            job_id=None,
            status=self.status,
            message=self.message,
            estimated_time=None,
            webhook_url=None,
            data=self.results,
        )


class CollectionWorkflow:
    """High-level orchestration for collection batch flows."""

    def __init__(self, job_service: JobService | None = None):
        self.job_service = job_service or JobService()

    @staticmethod
    def build_batch_plan(request: CollectionRequest) -> BatchCollectionPlan:
        return CollectionWorkflow.build_batch_plan_from_values(
            request.date,
            request.meet,
            request.race_numbers,
        )

    @staticmethod
    def build_batch_plan_from_values(
        race_date: str, meet: int, race_numbers: list[int] | None
    ) -> BatchCollectionPlan:
        race_numbers = race_numbers or list(range(1, 16))
        return BatchCollectionPlan(
            race_date=race_date,
            meet=meet,
            race_numbers=race_numbers,
        )

    async def collect_batch(
        self,
        plan: BatchCollectionPlan,
        db: AsyncSession,
        kra_api: KRAAPIService,
    ) -> BatchCollectionOutcome:
        """Collect a batch of races with centralized partial-failure handling."""
        collection_service = CollectionService(kra_api)
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        logger.info(
            "Collecting batch races",
            race_date=plan.race_date,
            meet=plan.meet,
            race_numbers=plan.race_numbers,
        )

        for race_no in plan.race_numbers:
            try:
                result = await collection_service.collect_race_data(
                    plan.race_date,
                    plan.meet,
                    race_no,
                    db,
                )
                results.append(result)
                logger.info("Collected race", race_no=race_no)
            except Exception as exc:
                logger.error(
                    "Batch collection failed for race",
                    race_no=race_no,
                    error=str(exc),
                    exc_info=True,
                )
                errors.append({"race_no": race_no, "error": str(exc)})

        if not results and errors:
            return BatchCollectionOutcome(
                status="error",
                message="All requested races failed to collect",
                results=[],
                errors=errors,
            )

        status = "success" if not errors else "partial"
        message = f"Collected {len(results)} races"
        if errors:
            message = f"Collected {len(results)} races, failed {len(errors)} races"

        return BatchCollectionOutcome(
            status=status,
            message=message,
            results=results,
            errors=errors,
        )

    async def submit_batch_job(
        self,
        plan: BatchCollectionPlan,
        *,
        owner_ref: str,
        db: AsyncSession,
    ) -> CollectionResponse:
        """Submit async batch collection via the shared job service."""
        parameters = {
            "race_date": plan.race_date,
            "meet": plan.meet,
            "race_numbers": plan.race_numbers,
        }

        job = await self.job_service.create_job(
            job_type="batch",
            parameters=parameters,
            owner_ref=owner_ref,
            db=db,
        )
        job_id = str(job.job_id)
        await self.job_service.start_job(job_id, db)

        return CollectionResponse(
            job_id=job_id,
            status="accepted",
            message="Collection job started",
            webhook_url=f"/api/v2/jobs/{job_id}",
            data=None,
            estimated_time=5,
        )
