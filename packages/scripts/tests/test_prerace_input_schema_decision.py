from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_input_schema_decision import (  # noqa: E402
    DECISION_PRIORITY_ORDER,
    INPUT_SCHEMA_DECISION_VERSION,
    SCHEMA_DECISION_EXAMPLES,
    SCHEMA_DECISION_RULES,
    SCHEMA_DECISIONS,
    InputSchemaDecisionInput,
    decide_input_schema,
)


def test_input_schema_decision_version_is_fixed() -> None:
    assert INPUT_SCHEMA_DECISION_VERSION == "prerace-input-schema-decision-v1"


def test_decision_enums_and_priority_order_are_explicit() -> None:
    assert SCHEMA_DECISIONS == ("ALLOW", "BLOCK", "REVIEW_REQUIRED")
    assert DECISION_PRIORITY_ORDER == ("BLOCK", "REVIEW_REQUIRED", "ALLOW")
    assert [rule.rule_id for rule in SCHEMA_DECISION_RULES] == [
        "block_postrace_or_leakage_signal",
        "block_non_feature_scope",
        "review_unverified_timing_signal",
        "review_inconsistent_allowed_contract",
        "allow_explicit_prerace_contract",
        "review_fallback_incomplete_schema",
    ]
    assert [rule.priority for rule in SCHEMA_DECISION_RULES] == [
        100,
        90,
        80,
        70,
        10,
        0,
    ]


def test_representative_schema_examples_cover_allow_block_review() -> None:
    observed = {example.expected_verdict for example in SCHEMA_DECISION_EXAMPLES}
    assert observed == {"ALLOW", "BLOCK", "REVIEW_REQUIRED"}

    for example in SCHEMA_DECISION_EXAMPLES:
        result = decide_input_schema(example.schema)
        assert result.verdict == example.expected_verdict, example.case_id
        assert result.rule_id == example.expected_rule_id, example.case_id


def test_postrace_signal_overrides_nominal_allow_flag() -> None:
    result = decide_input_schema(
        InputSchemaDecisionInput(
            field_path="race_plan.rank",
            consumer_scope="train_inference",
            availability_stage="L0",
            as_of_requirement="POSTRACE_ONLY",
            train_inference_flag="ALLOW",
            allowed_data_category="race_plan_direct",
            time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
            generated_at_kind="SOURCE_PUBLICATION_TIME",
            updated_at_kind="POSTRACE_CONFIRMATION_TIME",
            identifier_kind="canonical_path",
            identifier_pattern="race_plan.rank",
            identifier_source_tags=("pre_entry_allowed", "post_entry_only"),
        )
    )

    assert result.verdict == "BLOCK"
    assert result.rule_id == "block_postrace_or_leakage_signal"


def test_unverified_signal_overrides_nominal_snapshot_allow_flag() -> None:
    result = decide_input_schema(
        InputSchemaDecisionInput(
            field_path="track.weather",
            consumer_scope="train_inference",
            availability_stage="?",
            as_of_requirement="TIMING_UNVERIFIED",
            train_inference_flag="ALLOW_SNAPSHOT_ONLY",
            allowed_data_category="snapshot_locked_race_state",
            time_boundary_rule="MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE",
            generated_at_kind="UNVERIFIED_TIME",
            updated_at_kind="UNVERIFIED_TIME",
            identifier_kind="canonical_path",
            identifier_pattern="track.weather",
            identifier_source_tags=("snapshot_only", "hold"),
        )
    )

    assert result.verdict == "REVIEW_REQUIRED"
    assert result.rule_id == "review_unverified_timing_signal"


def test_inconsistent_snapshot_contract_requires_review() -> None:
    result = decide_input_schema(
        InputSchemaDecisionInput(
            field_path="track.weather",
            consumer_scope="train_inference",
            availability_stage="L0",
            as_of_requirement="DIRECT_PRE_RACE",
            train_inference_flag="ALLOW_SNAPSHOT_ONLY",
            allowed_data_category="snapshot_locked_race_state",
            time_boundary_rule="VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
            generated_at_kind="SNAPSHOT_COLLECTION_TIME",
            updated_at_kind="SNAPSHOT_COLLECTION_TIME",
            identifier_kind="canonical_path",
            identifier_pattern="track.weather",
            identifier_source_tags=("snapshot_only",),
        )
    )

    assert result.verdict == "REVIEW_REQUIRED"
    assert result.rule_id == "review_inconsistent_allowed_contract"


def test_mapping_input_is_supported() -> None:
    result = decide_input_schema(
        {
            "field_path": "horses[].jkDetail.winRateT",
            "consumer_scope": "train_inference",
            "availability_stage": "L-1",
            "as_of_requirement": "STORED_AS_OF_SNAPSHOT",
            "train_inference_flag": "ALLOW_STORED_ONLY",
            "allowed_data_category": "stored_detail_lookup",
            "time_boundary_rule": "STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
            "generated_at_kind": "STORED_AS_OF_TIME",
            "updated_at_kind": "STORED_AS_OF_TIME",
            "identifier_kind": "canonical_path",
            "identifier_pattern": "horses[].jkDetail.winRateT",
            "identifier_source_tags": "stored_only",
            "exception_rule": "KEEP_STORED_AS_OF_SNAPSHOT",
        }
    )

    assert result.verdict == "ALLOW"
    assert result.rule_id == "allow_explicit_prerace_contract"
