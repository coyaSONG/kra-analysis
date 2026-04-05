"""
Canonical job vocabulary used internally by the job service layer.
"""

from enum import Enum


class DispatchAction(str, Enum):
    COLLECT_RACE = "collect_race"
    PREPROCESS_RACE = "preprocess_race"
    ENRICH_RACE = "enrich_race"
    BATCH_COLLECT = "batch_collect"
    FULL_PIPELINE = "full_pipeline"


class LifecycleStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def normalize_job_kind(value: object) -> str:
    raw = value.value if hasattr(value, "value") else str(value)
    alias_map: dict[str, str] = {
        "collection": "collection",
        "collect_race": DispatchAction.COLLECT_RACE.value,
        "preprocess_race": DispatchAction.PREPROCESS_RACE.value,
        "enrichment": "enrichment",
        "enrich_race": DispatchAction.ENRICH_RACE.value,
        "analysis": "analysis",
        "prediction": "prediction",
        "improvement": "improvement",
        "batch": DispatchAction.BATCH_COLLECT.value,
        "batch_collect": DispatchAction.BATCH_COLLECT.value,
        "full_pipeline": DispatchAction.FULL_PIPELINE.value,
    }
    try:
        return alias_map[raw]
    except KeyError as exc:
        raise ValueError(f"Unknown job kind: {raw}") from exc


def normalize_dispatch_action(value: object) -> DispatchAction:
    raw = value.value if hasattr(value, "value") else str(value)
    alias_map: dict[str, DispatchAction] = {
        "collect_race": DispatchAction.COLLECT_RACE,
        "collection": DispatchAction.COLLECT_RACE,
        "preprocess_race": DispatchAction.PREPROCESS_RACE,
        "enrich_race": DispatchAction.ENRICH_RACE,
        "enrichment": DispatchAction.ENRICH_RACE,
        "batch_collect": DispatchAction.BATCH_COLLECT,
        "batch": DispatchAction.BATCH_COLLECT,
        "full_pipeline": DispatchAction.FULL_PIPELINE,
    }
    try:
        return alias_map[raw]
    except KeyError as exc:
        raise ValueError(f"Unknown job type: {raw}") from exc


def normalize_lifecycle_status(value: object) -> LifecycleStatus:
    raw = value.value if hasattr(value, "value") else str(value)
    alias_map: dict[str, LifecycleStatus] = {
        "pending": LifecycleStatus.PENDING,
        "queued": LifecycleStatus.QUEUED,
        "processing": LifecycleStatus.PROCESSING,
        "running": LifecycleStatus.PROCESSING,
        "completed": LifecycleStatus.COMPLETED,
        "failed": LifecycleStatus.FAILED,
        "cancelled": LifecycleStatus.CANCELLED,
    }
    try:
        return alias_map[raw]
    except KeyError as exc:
        raise ValueError(f"Unknown lifecycle status: {raw}") from exc


def apply_job_shadow_fields(
    job: object,
    *,
    job_kind: object | None = None,
    lifecycle_status: object | None = None,
) -> None:
    source_kind = job_kind if job_kind is not None else getattr(job, "type", None)
    if source_kind is not None:
        job.job_kind_v2 = normalize_job_kind(source_kind)

    source_status = (
        lifecycle_status if lifecycle_status is not None else getattr(job, "status", None)
    )
    if source_status is not None:
        job.lifecycle_state_v2 = normalize_lifecycle_status(source_status).value
