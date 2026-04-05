from types import SimpleNamespace

import pytest

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


def test_normalize_lifecycle_status_accepts_running_alias():
    assert normalize_lifecycle_status("running") is LifecycleStatus.PROCESSING
    assert normalize_lifecycle_status("processing") is LifecycleStatus.PROCESSING


def test_normalize_job_kind_accepts_batch_alias():
    assert normalize_job_kind("batch") == DispatchAction.BATCH_COLLECT.value
    assert normalize_job_kind("collection") == "collection"


def test_apply_job_shadow_fields_writes_normalized_values():
    job = SimpleNamespace(type="batch", status="running")
    apply_job_shadow_fields(job)

    assert job.job_kind_v2 == DispatchAction.BATCH_COLLECT.value
    assert job.lifecycle_state_v2 == LifecycleStatus.PROCESSING.value


def test_normalize_dispatch_action_rejects_unknown_value():
    with pytest.raises(ValueError, match="Unknown job type"):
        normalize_dispatch_action("unknown")
