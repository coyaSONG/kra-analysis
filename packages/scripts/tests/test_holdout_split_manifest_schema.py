from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.batch_race_selection_policy import (  # noqa: E402
    BATCH_RACE_SELECTION_POLICY_VERSION,
)
from shared.holdout_split_manifest_schema import (  # noqa: E402
    DEFAULT_ENTRY_FINALIZATION_RULE_VERSION,
    DEFAULT_RECENT_HOLDOUT_RULE_VERSION,
    HOLDOUT_SPLIT_MANIFEST_VERSION,
    HoldoutSplitManifest,
    holdout_split_manifest_json_schema,
    validate_holdout_split_manifest,
)


def _build_manifest_payload() -> dict:
    return {
        "format_version": HOLDOUT_SPLIT_MANIFEST_VERSION,
        "parameters": {
            "dataset": "holdout",
            "selection_method": "time_ordered_complete_date_accumulation",
            "boundary_unit": "race_date",
            "minimum_race_count": 500,
            "require_complete_race_dates": True,
            "allow_intra_day_cut": False,
            "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
            "target_label": "unordered_top3",
            "leakage_policy_version": "leakage-checks-v1",
        },
        "metadata": {
            "manifest_created_at": "2026-04-10T12:00:00+09:00",
            "period": {
                "start_date": "2025-10-19",
                "end_date": "2026-02-14",
                "latest_complete_race_date": "2026-02-14",
                "race_count": 500,
                "race_date_count": 34,
                "accumulation_direction": "backward_from_latest_complete_date",
            },
            "seed": {
                "selection_seed": None,
                "selection_seed_invariant": True,
                "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61],
            },
            "data_snapshot": {
                "data_as_of": "2026-02-14T18:00:00+09:00",
                "results_as_of": "2026-02-14T19:00:00+09:00",
                "entry_snapshot_as_of": "2026-02-14T17:50:00+09:00",
            },
            "rule": {
                "rule_version": DEFAULT_RECENT_HOLDOUT_RULE_VERSION,
                "rule_path": "docs/recent-holdout-split-rule.md",
                "entry_finalization_rule_version": DEFAULT_ENTRY_FINALIZATION_RULE_VERSION,
                "batch_race_selection_policy_version": BATCH_RACE_SELECTION_POLICY_VERSION,
            },
        },
        "included_race_ids": ("race-1", "race-2", "race-3"),
        "race_input_snapshot_map": {
            "race-1": {
                "snapshot_id": "holdout-input-v1:1111111111111111",
                "snapshot_generation_basis": {
                    "source_filter_basis": "entry_finalized_at",
                    "timestamp_source": "snapshot_collected_at",
                    "selected_timestamp_field": "basic_data.collected_at",
                    "selected_timestamp_value": "2026-02-14T17:50:00+09:00",
                    "snapshot_ready_at": "2026-02-14T17:50:00+09:00",
                    "entry_finalized_at": "2026-02-14T17:50:00+09:00",
                },
            },
            "race-2": {
                "snapshot_id": "holdout-input-v1:2222222222222222",
                "snapshot_generation_basis": {
                    "source_filter_basis": "entry_finalized_at",
                    "timestamp_source": "snapshot_collected_at",
                    "selected_timestamp_field": "races.collected_at",
                    "selected_timestamp_value": "2026-02-14T17:49:00+09:00",
                    "snapshot_ready_at": "2026-02-14T17:49:00+09:00",
                    "entry_finalized_at": "2026-02-14T17:49:00+09:00",
                },
            },
            "race-3": {
                "snapshot_id": "holdout-input-v1:3333333333333333",
                "snapshot_generation_basis": {
                    "source_filter_basis": "entry_finalized_at",
                    "timestamp_source": "derived_from_schedule",
                    "selected_timestamp_field": "race_plan.sch_st_time_minus_10m",
                    "selected_timestamp_value": "2026-02-14T17:48:00+09:00",
                    "snapshot_ready_at": None,
                    "entry_finalized_at": "2026-02-14T17:48:00+09:00",
                },
            },
        },
        "excluded_race_dates": ("2026-02-15",),
        "exclusion_reason_counts": {"missing_basic_data": 4},
        "manifest_sha256": "abc123def4567890",
    }


def test_manifest_schema_version_is_fixed() -> None:
    assert HOLDOUT_SPLIT_MANIFEST_VERSION == "holdout-split-manifest-v1"


def test_json_schema_requires_parameters_and_metadata_blocks() -> None:
    schema = holdout_split_manifest_json_schema()

    assert schema["title"] == "HoldoutSplitManifest"
    assert "parameters" in schema["required"]
    assert "metadata" in schema["required"]
    assert "included_race_ids" in schema["required"]
    assert "race_input_snapshot_map" in schema["required"]


def test_manifest_accepts_seed_invariant_holdout_contract() -> None:
    payload = _build_manifest_payload()

    manifest = HoldoutSplitManifest.model_validate(payload)

    assert manifest.parameters.minimum_race_count == 500
    assert manifest.metadata.period.start_date.isoformat() == "2025-10-19"
    assert manifest.metadata.seed.selection_seed is None
    assert len(manifest.metadata.seed.evaluation_seeds) == 10
    assert manifest.metadata.rule.rule_version == DEFAULT_RECENT_HOLDOUT_RULE_VERSION
    assert (
        manifest.metadata.rule.batch_race_selection_policy_version
        == BATCH_RACE_SELECTION_POLICY_VERSION
    )
    assert (
        manifest.race_input_snapshot_map[
            "race-1"
        ].snapshot_generation_basis.selected_timestamp_field
        == "basic_data.collected_at"
    )


def test_manifest_rejects_missing_metadata_blocks() -> None:
    payload = _build_manifest_payload()
    del payload["metadata"]["data_snapshot"]

    ok, errors = validate_holdout_split_manifest(payload)

    assert ok is False
    assert any("metadata.data_snapshot" in error for error in errors)


def test_manifest_rejects_non_invariant_selection_seed_contract() -> None:
    payload = _build_manifest_payload()
    payload["metadata"]["seed"]["selection_seed"] = 7

    ok, errors = validate_holdout_split_manifest(payload)

    assert ok is False
    assert any("selection_seed" in error for error in errors)


def test_manifest_rejects_seed_lists_other_than_10_distinct_runs() -> None:
    payload = _build_manifest_payload()
    payload["metadata"]["seed"]["evaluation_seeds"] = [
        11,
        17,
        23,
        31,
        37,
        41,
        47,
        53,
        59,
    ]

    ok, errors = validate_holdout_split_manifest(payload)

    assert ok is False
    assert any("정확히 10개" in error for error in errors)


def test_manifest_rejects_missing_race_input_snapshot_mapping() -> None:
    payload = _build_manifest_payload()
    del payload["race_input_snapshot_map"]["race-3"]

    ok, errors = validate_holdout_split_manifest(payload)

    assert ok is False
    assert any("race_input_snapshot_map" in error for error in errors)
