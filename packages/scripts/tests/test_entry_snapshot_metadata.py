from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.entry_snapshot_metadata import (  # noqa: E402
    build_entry_snapshot_metadata,
    derive_or_restore_entry_snapshot_metadata,
)


def _basic_data(*, collected_at: str = "2025-01-01T10:35:00+09:00") -> dict:
    return {
        "collected_at": collected_at,
        "race_info": {
            "response": {"body": {"items": {"item": [{"schStTime": "1100"}]}}}
        },
        "race_plan": {"sch_st_time": "1100"},
        "track": {"weather": "맑음"},
        "cancelled_horses": [],
        "horses": [{"chul_no": 1}],
    }


def test_build_entry_snapshot_metadata_uses_basic_data_collected_at() -> None:
    meta = build_entry_snapshot_metadata(
        race_date="20250101",
        basic_data=_basic_data(),
    )

    assert meta.timestamp_source == "snapshot_collected_at"
    assert meta.timestamp_confidence == "medium"
    assert meta.selected_timestamp_field == "basic_data.collected_at"
    assert meta.scheduled_start_at == "2025-01-01T11:00:00+09:00"
    assert meta.operational_cutoff_at == "2025-01-01T10:50:00+09:00"
    assert meta.entry_finalized_at == "2025-01-01T10:35:00+09:00"
    assert meta.replay_status == "strict"
    assert meta.include_in_strict_dataset is True
    assert meta.hard_required_sources_present is True
    assert meta.hard_required_source_status == {
        "API214_1": "present",
        "API72_2": "present",
        "API189_1": "present",
        "API9_1": "present",
    }


def test_build_entry_snapshot_metadata_uses_explicit_entry_finalized_override() -> None:
    meta = build_entry_snapshot_metadata(
        race_date="20250101",
        basic_data=_basic_data(collected_at="2025-01-01T10:55:00+09:00"),
        entry_finalized_at_override="2025-01-01T10:45:00+09:00",
        revision_id="rev-001",
    )

    assert meta.timestamp_source == "source_revision"
    assert meta.timestamp_confidence == "high"
    assert meta.selected_timestamp_field == "entry_finalized_at_override"
    assert meta.entry_finalized_at == "2025-01-01T10:45:00+09:00"
    assert meta.snapshot_ready_at == "2025-01-01T10:45:00+09:00"
    assert meta.revision_id == "rev-001"
    assert meta.replay_status == "strict"


def test_derive_or_restore_entry_snapshot_metadata_prefers_persisted_raw_data() -> None:
    raw_data = {
        "snapshot_meta": {
            "format_version": "holdout-snapshot-v1",
            "rule_version": "holdout-entry-finalization-rule-v1",
            "source_filter_basis": "entry_finalized_at",
            "scheduled_start_at": "2025-01-01T11:00:00+09:00",
            "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
            "snapshot_ready_at": "2025-01-01T10:40:00+09:00",
            "entry_finalized_at": "2025-01-01T10:40:00+09:00",
            "selected_timestamp_field": "entry_finalized_at_override",
            "selected_timestamp_value": "2025-01-01T10:40:00+09:00",
            "timestamp_source": "source_revision",
            "timestamp_confidence": "high",
            "revision_id": "rev-777",
            "late_reissue_after_cutoff": False,
            "cutoff_unbounded": False,
            "replay_status": "strict",
            "include_in_strict_dataset": True,
            "hard_required_sources_present": True,
            "hard_required_source_status": {
                "API214_1": "present",
                "API72_2": "present",
                "API189_1": "present",
                "API9_1": "present",
            },
        }
    }

    meta = derive_or_restore_entry_snapshot_metadata(
        race_date="20250101",
        basic_data=_basic_data(),
        raw_data=raw_data,
        row_collected_at="2025-01-01T10:35:00+09:00",
        row_updated_at="2025-01-01T10:36:00+09:00",
    )

    assert meta.timestamp_source == "source_revision"
    assert meta.timestamp_confidence == "high"
    assert meta.selected_timestamp_field == "entry_finalized_at_override"
    assert meta.entry_finalized_at == "2025-01-01T10:40:00+09:00"
    assert meta.revision_id == "rev-777"


def test_build_entry_snapshot_metadata_marks_partial_snapshot_when_required_sources_missing() -> (
    None
):
    basic_data = _basic_data()
    del basic_data["track"]

    meta = build_entry_snapshot_metadata(
        race_date="20250101",
        basic_data=basic_data,
    )

    assert meta.hard_required_sources_present is False
    assert meta.replay_status == "partial_snapshot"
    assert meta.include_in_strict_dataset is False
    assert meta.hard_required_source_status["API189_1"] == "missing"
