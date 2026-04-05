"""
Public collection facade for API routes.

This module groups read-only status queries, synchronous collection commands,
and asynchronous job submission behind one entry point.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.collection_service import CollectionService
from services.job_service import JobService
from services.kra_api_service import KRAAPIService, get_kra_api_service
from services.race_processing_workflow import (
    CollectRaceCommand,
    RaceKey,
    build_race_processing_workflow,
)
from services.result_collection_service import ResultCollectionService

_DEFAULT_RACE_NUMBERS = list(range(1, 16))


@dataclass(frozen=True, slots=True)
class BatchCollectInput:
    race_date: str
    meet: int
    race_numbers: Sequence[int] | None = None


@dataclass(frozen=True, slots=True)
class ResultCollectInput:
    race_date: str
    meet: int
    race_number: int


@dataclass(frozen=True, slots=True)
class CollectionStatusSnapshot:
    date: str
    meet: int
    total_races: int
    collected_races: int
    enriched_races: int
    status: str
    collection_status: str | None
    enrichment_status: str | None
    result_status: str | None
    last_updated: Any | None


@dataclass(frozen=True, slots=True)
class CollectionOutcome:
    status: str
    message: str
    data: list[dict[str, Any]]
    errors: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class JobReceipt:
    job_id: str
    status: str
    message: str
    webhook_url: str | None
    estimated_time: int | None


def _normalize_race_numbers(race_numbers: Sequence[int] | None) -> list[int]:
    return list(race_numbers) if race_numbers else list(_DEFAULT_RACE_NUMBERS)


class CollectionQueries:
    async def get_status(
        self, *, race_date: str, meet: int, db: AsyncSession
    ) -> CollectionStatusSnapshot:
        payload = await CollectionService.get_collection_status(db, race_date, meet)
        return CollectionStatusSnapshot(**payload)


class CollectionCommands:
    def __init__(
        self,
        *,
        result_collection_service: ResultCollectionService | None = None,
    ):
        self.result_collection_service = (
            result_collection_service or ResultCollectionService()
        )

    async def _get_kra_api(self) -> KRAAPIService:
        return await get_kra_api_service()

    def _build_workflow(self, kra_api: KRAAPIService, db: AsyncSession):
        return build_race_processing_workflow(kra_api, db)

    async def collect_batch(
        self, request: BatchCollectInput, *, db: AsyncSession
    ) -> CollectionOutcome:
        kra_api = await self._get_kra_api()
        workflow = self._build_workflow(kra_api, db)

        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for race_no in _normalize_race_numbers(request.race_numbers):
            try:
                result = await workflow.collect(
                    CollectRaceCommand(
                        key=RaceKey(
                            race_date=request.race_date,
                            meet=request.meet,
                            race_number=race_no,
                        )
                    )
                )
                results.append(result.payload)
            except Exception as exc:
                errors.append({"race_no": race_no, "error": str(exc)})

        if not results and errors:
            return CollectionOutcome(
                status="error",
                message="All requested races failed to collect",
                data=[],
                errors=errors,
            )

        message = f"Collected {len(results)} races"
        if errors:
            message = f"Collected {len(results)} races, failed {len(errors)} races"

        return CollectionOutcome(
            status="success" if not errors else "partial",
            message=message,
            data=results,
            errors=errors,
        )

    async def collect_result(
        self, request: ResultCollectInput, *, db: AsyncSession
    ) -> dict[str, Any]:
        kra_api = await self._get_kra_api()
        return await self.result_collection_service.collect_result(
            race_date=request.race_date,
            meet=request.meet,
            race_number=request.race_number,
            db=db,
            kra_api=kra_api,
        )


class CollectionJobs:
    def __init__(self, *, job_service: JobService | None = None):
        self.job_service = job_service or JobService()

    async def submit_batch_collect(
        self,
        request: BatchCollectInput,
        *,
        owner_ref: str,
        db: AsyncSession,
    ) -> JobReceipt:
        parameters = {
            "race_date": request.race_date,
            "meet": request.meet,
            "race_numbers": _normalize_race_numbers(request.race_numbers),
        }

        job = await self.job_service.create_job(
            job_type="batch",
            parameters=parameters,
            owner_ref=owner_ref,
            db=db,
        )
        job_id = str(job.job_id)
        await self.job_service.start_job(job_id, db)

        return JobReceipt(
            job_id=job_id,
            status="accepted",
            message="Collection job started",
            webhook_url=f"/api/v2/jobs/{job_id}",
            estimated_time=5,
        )


class KRACollectionModule:
    def __init__(
        self,
        *,
        queries: CollectionQueries | None = None,
        commands: CollectionCommands | None = None,
        jobs: CollectionJobs | None = None,
    ):
        self.queries = queries or CollectionQueries()
        self.commands = commands or CollectionCommands()
        self.jobs = jobs or CollectionJobs()
