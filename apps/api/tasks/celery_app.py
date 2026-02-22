"""Celery application bootstrap for job runner mode."""

from functools import lru_cache
from typing import Any

from config import settings

try:
    from celery import Celery
except ImportError:  # pragma: no cover - exercised only when celery is not installed
    Celery = None


def _require_celery() -> Any:
    if Celery is None:
        raise RuntimeError(
            "Celery package is not installed. Install celery or set JOB_RUNNER_MODE=inprocess."
        )
    return Celery


@lru_cache(maxsize=1)
def get_celery_app():
    celery_cls = _require_celery()
    app = celery_cls("kra-api")
    app.conf.update(
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        task_always_eager=settings.celery_task_always_eager,
        task_eager_propagates=settings.celery_task_eager_propagates,
        task_store_eager_result=settings.celery_task_store_eager_result,
        task_track_started=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        imports=("tasks.celery_tasks",),
    )
    return app


def reset_celery_app_cache() -> None:
    """Reset singleton Celery app cache (used in tests)."""
    get_celery_app.cache_clear()
