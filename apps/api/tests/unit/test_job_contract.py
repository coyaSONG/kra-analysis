from types import SimpleNamespace

import pytest

from models.database_models import JobStatus as ORMJobStatus
from models.job_dto import JobStatus as DTOJobStatus
from services.job_contract import (
    DispatchAction,
    LifecycleStatus,
    apply_job_shadow_fields,
    normalize_dispatch_action,
    normalize_job_kind,
    normalize_lifecycle_status,
)


def test_normalize_dispatch_action_accepts_batch_alias():
    assert normalize_dispatch_action("batch") is DispatchAction.BATCH_COLLECT
    assert normalize_dispatch_action("batch_collect") is DispatchAction.BATCH_COLLECT
    assert normalize_dispatch_action("analysis") is DispatchAction.ANALYSIS
    assert normalize_dispatch_action("prediction") is DispatchAction.PREDICTION
    assert normalize_dispatch_action("improvement") is DispatchAction.IMPROVEMENT


def test_normalize_lifecycle_status_accepts_running_alias():
    assert normalize_lifecycle_status("running") is LifecycleStatus.PROCESSING
    assert normalize_lifecycle_status("processing") is LifecycleStatus.PROCESSING
    assert normalize_lifecycle_status("retrying") is LifecycleStatus.PROCESSING


def test_public_job_status_enums_exclude_internal_aliases():
    dto_statuses = {status.value for status in DTOJobStatus}
    orm_statuses = {status.value for status in ORMJobStatus}

    assert dto_statuses == {
        "pending",
        "queued",
        "processing",
        "completed",
        "failed",
        "cancelled",
    }
    assert orm_statuses == dto_statuses


def test_normalize_job_kind_preserves_public_kind_for_persistence():
    assert normalize_job_kind("batch") == "batch"
    assert normalize_job_kind("batch_collect") == "batch"
    assert normalize_job_kind("collection") == "collection"


def test_apply_job_shadow_fields_mirrors_public_vocabulary():
    job = SimpleNamespace(type="batch", status="running")
    apply_job_shadow_fields(job)

    assert job.job_kind_v2 == "batch"
    assert job.lifecycle_state_v2 == LifecycleStatus.PROCESSING.value


def test_normalize_dispatch_action_rejects_unknown_value():
    with pytest.raises(ValueError, match="Unknown job type"):
        normalize_dispatch_action("unknown")
