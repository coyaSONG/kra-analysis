from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_field_validation_metaschema import (  # noqa: E402
    ALL_COLUMNS,
    ALLOWED_DATA_CATEGORIES,
    CANONICAL_STORAGE_ENCODING,
    CANONICAL_STORAGE_RELATIVE_PATH,
    CONSUMER_SCOPES,
    EXCEPTION_RULE_TYPES,
    FIELD_VALIDATION_SPEC_ROWS,
    IDENTIFIER_KINDS,
    REQUIRED_COLUMNS,
    TIME_BOUNDARY_RULES,
    TIME_REFERENCE_TYPES,
    VALIDATION_SPEC_VERSION,
    canonical_validation_spec_rows,
    csv_header,
    forbidden_post_race_validation_rows,
    validation_rows_by_category,
    validation_spec_row_by_field_path,
)


def test_validation_spec_version_is_fixed() -> None:
    assert VALIDATION_SPEC_VERSION == "prerace-field-validation-spec-v1"


def test_required_columns_cover_sub_ac_contract() -> None:
    required = set(REQUIRED_COLUMNS)
    assert "field_path" in required
    assert "data_source" in required
    assert "generated_at_basis" in required
    assert "updated_at_basis" in required
    assert "judgment_basis" in required
    assert "judgment_basis_refs" in required
    assert "identifier_kind" in required
    assert "identifier_pattern" in required
    assert "identifier_aliases" in required
    assert "identifier_source_tags" in required
    assert "allowed_data_category" in required
    assert "time_boundary_rule" in required
    assert "exception_rule" in required


def test_enum_sets_remain_explicit() -> None:
    assert CONSUMER_SCOPES == (
        "train_inference",
        "label_only",
        "metadata_only",
    )
    assert TIME_REFERENCE_TYPES == (
        "SOURCE_PUBLICATION_TIME",
        "SNAPSHOT_COLLECTION_TIME",
        "STORED_AS_OF_TIME",
        "DERIVED_PARENT_LOCK_TIME",
        "POSTRACE_CONFIRMATION_TIME",
        "UNVERIFIED_TIME",
    )
    assert IDENTIFIER_KINDS == (
        "canonical_path",
        "leaf_key",
        "prefix_path",
        "regex_pattern",
    )
    assert ALLOWED_DATA_CATEGORIES == (
        "core_card_direct",
        "race_plan_direct",
        "snapshot_locked_race_state",
        "stored_detail_lookup",
        "historical_aggregate",
        "timing_unverified_market",
        "postrace_feedback",
        "label_result",
        "metadata_anchor",
    )
    assert TIME_BOUNDARY_RULES == (
        "VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        "SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        "STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        "LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE",
        "MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE",
        "GENERATED_AFTER_RESULT_CONFIRMATION",
    )
    assert EXCEPTION_RULE_TYPES == (
        "NONE",
        "ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT",
        "KEEP_LOCKED_SNAPSHOT",
        "KEEP_STORED_AS_OF_SNAPSHOT",
        "STRICT_PAST_ONLY",
        "SOFT_FAIL_EMPTY_BLOCK",
        "RAW_STORE_ONLY",
        "LABEL_RECOMPUTE_ONLY",
        "METADATA_RETAIN_ONLY",
    )


def test_validation_spec_rows_cover_core_allowability_cases() -> None:
    assert FIELD_VALIDATION_SPEC_ROWS

    assert (
        validation_spec_row_by_field_path("horses[].chul_no").allowed_data_category
        == "core_card_direct"
    )
    assert (
        validation_spec_row_by_field_path("horses[].chul_no").exception_rule
        == "ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT"
    )
    assert (
        validation_spec_row_by_field_path("race_plan.rank").train_inference_flag
        == "ALLOW"
    )
    assert (
        validation_spec_row_by_field_path("race_plan.rank").allowed_data_category
        == "race_plan_direct"
    )
    assert (
        validation_spec_row_by_field_path("track.weather").train_inference_flag
        == "ALLOW_SNAPSHOT_ONLY"
    )
    assert (
        validation_spec_row_by_field_path("horses[].training").exception_rule
        == "SOFT_FAIL_EMPTY_BLOCK"
    )
    assert (
        validation_spec_row_by_field_path(
            "horses[].jkDetail.winRateT"
        ).train_inference_flag
        == "ALLOW_STORED_ONLY"
    )
    assert (
        validation_spec_row_by_field_path(
            "horses[].past_stats.recent_top3_rate"
        ).time_boundary_rule
        == "LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE"
    )
    assert (
        validation_spec_row_by_field_path("horses[].win_odds").train_inference_flag
        == "HOLD"
    )
    assert (
        validation_spec_row_by_field_path("race_odds.win").train_inference_flag
        == "BLOCK"
    )
    assert (
        validation_spec_row_by_field_path("result_data.top3").train_inference_flag
        == "LABEL_ONLY"
    )
    assert validation_spec_row_by_field_path("finish_position").identifier_aliases == (
        "rank",
        "ord",
    )
    assert validation_spec_row_by_field_path("rcTime").identifier_aliases == (
        "resultTime",
    )
    assert validation_spec_row_by_field_path("payout").identifier_aliases == (
        "dividend",
    )
    assert (
        validation_spec_row_by_field_path(
            "sectional_live_metric_pattern"
        ).identifier_kind
        == "regex_pattern"
    )
    assert (
        validation_spec_row_by_field_path(
            "snapshot_meta.entry_finalized_at"
        ).train_inference_flag
        == "META_ONLY"
    )


def test_validation_spec_registers_rows_for_each_category() -> None:
    categories_with_rows = {
        category
        for category in ALLOWED_DATA_CATEGORIES
        if validation_rows_by_category(category)
    }
    assert categories_with_rows == set(ALLOWED_DATA_CATEGORIES)


def test_forbidden_post_race_rows_register_detection_rules() -> None:
    rows = forbidden_post_race_validation_rows()

    assert rows
    assert all(row.identifier_pattern for row in rows)
    assert all("post_entry_only" in row.identifier_source_tags for row in rows)
    assert all(
        row.time_boundary_rule == "GENERATED_AFTER_RESULT_CONFIRMATION" for row in rows
    )
    assert {row.field_path for row in rows} >= {
        "race_odds.win",
        "result_data.top3",
        "finish_position",
        "sectional_live_metric_pattern",
    }


def test_csv_template_matches_declared_rows() -> None:
    template_path = (
        Path(__file__).resolve().parents[3] / CANONICAL_STORAGE_RELATIVE_PATH
    )
    with template_path.open(encoding=CANONICAL_STORAGE_ENCODING, newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert tuple(rows[0].keys()) == ALL_COLUMNS
    assert csv_header() == ",".join(ALL_COLUMNS)
    assert rows == list(canonical_validation_spec_rows())
