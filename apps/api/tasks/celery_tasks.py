"""Celery task wrappers around async task implementations."""

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any

import structlog

from tasks.async_tasks import (
    batch_collect,
    collect_race_data,
    enrich_race_data,
    full_pipeline,
    preprocess_race_data,
)
from tasks.celery_app import get_celery_app

logger = structlog.get_logger()
celery_app = get_celery_app()


def _run_coroutine(coro: Coroutine[Any, Any, dict[str, Any]]) -> dict[str, Any]:
    """Run async coroutine from sync Celery task context."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: Exception | None = None

    def _runner() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(coro)
        except Exception as exc:  # pragma: no cover - surfaced to caller
            error = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if error is not None:
        raise error
    return result


@celery_app.task(bind=True, name="kra.collect_race_data")
def collect_race_data_task(
    self, race_date: str, meet: int, race_no: int, job_id: str | None = None
) -> dict[str, Any]:
    return _run_coroutine(
        collect_race_data(
            race_date=race_date,
            meet=meet,
            race_no=race_no,
            job_id=job_id,
            task_id=self.request.id,
        )
    )


@celery_app.task(bind=True, name="kra.preprocess_race_data")
def preprocess_race_data_task(
    self, race_id: str, job_id: str | None = None
) -> dict[str, Any]:
    return _run_coroutine(
        preprocess_race_data(
            race_id=race_id,
            job_id=job_id,
            task_id=self.request.id,
        )
    )


@celery_app.task(bind=True, name="kra.enrich_race_data")
def enrich_race_data_task(
    self, race_id: str, job_id: str | None = None
) -> dict[str, Any]:
    return _run_coroutine(
        enrich_race_data(
            race_id=race_id,
            job_id=job_id,
            task_id=self.request.id,
        )
    )


@celery_app.task(bind=True, name="kra.batch_collect")
def batch_collect_task(
    self, race_date: str, meet: int, race_numbers: list[int], job_id: str | None = None
) -> dict[str, Any]:
    return _run_coroutine(
        batch_collect(
            race_date=race_date,
            meet=meet,
            race_numbers=race_numbers,
            job_id=job_id,
            task_id=self.request.id,
        )
    )


@celery_app.task(bind=True, name="kra.full_pipeline")
def full_pipeline_task(
    self, race_date: str, meet: int, race_no: int, job_id: str | None = None
) -> dict[str, Any]:
    return _run_coroutine(
        full_pipeline(
            race_date=race_date,
            meet=meet,
            race_no=race_no,
            job_id=job_id,
            task_id=self.request.id,
        )
    )
