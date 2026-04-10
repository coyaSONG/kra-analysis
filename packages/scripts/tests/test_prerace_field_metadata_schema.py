from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_field_metadata_schema import (  # noqa: E402
    ALL_COLUMNS,
    AVAILABILITY_STAGES,
    CANONICAL_STORAGE_ENCODING,
    CANONICAL_STORAGE_RELATIVE_PATH,
    FIELD_METADATA_RULES,
    FIELD_ROLES,
    METADATA_SCHEMA_VERSION,
    OPERATIONAL_STATUSES,
    REQUIRED_COLUMNS,
    RULE_MATCH_TYPES,
    TRAIN_INFERENCE_FLAGS,
    VALIDATION_STATUSES,
    canonical_field_metadata_rows,
    csv_header,
    match_field_metadata_rule,
)


def test_metadata_schema_version_is_fixed():
    assert METADATA_SCHEMA_VERSION == "prerace-field-metadata-v1"


def test_required_columns_cover_sub_ac_contract():
    required = set(REQUIRED_COLUMNS)
    assert "field_path" in required
    assert "availability_stage" in required
    assert "publication_basis" in required
    assert "publication_basis_refs" in required
    assert "exception_rule" in required
    assert "validation_status" in required
    assert "validation_evidence" in required
    assert "train_inference_flag" in required


def test_enum_sets_remain_explicit():
    assert FIELD_ROLES == ("source", "derived", "metadata", "label")
    assert AVAILABILITY_STAGES == ("L-1", "L0", "L0 snapshot", "?", "L+1")
    assert VALIDATION_STATUSES == (
        "documented",
        "measured",
        "pending_measurement",
        "rejected",
    )
    assert TRAIN_INFERENCE_FLAGS == (
        "ALLOW",
        "ALLOW_SNAPSHOT_ONLY",
        "ALLOW_STORED_ONLY",
        "HOLD",
        "BLOCK",
        "LABEL_ONLY",
        "META_ONLY",
    )
    assert "보류" in OPERATIONAL_STATUSES
    assert "금지" in OPERATIONAL_STATUSES


def test_rule_registry_covers_pre_post_entry_finalization_boundaries():
    assert RULE_MATCH_TYPES == ("exact", "prefix", "leaf")
    assert FIELD_METADATA_RULES

    assert match_field_metadata_rule("horses[0].rank").train_inference_flag == "ALLOW"
    assert match_field_metadata_rule("race_plan.rank").train_inference_flag == "ALLOW"
    assert match_field_metadata_rule("horses[0].winOdds").train_inference_flag == "HOLD"
    assert (
        match_field_metadata_rule("track.weather").train_inference_flag
        == "ALLOW_SNAPSHOT_ONLY"
    )
    assert (
        match_field_metadata_rule("horses[0].jkDetail.winRateT").train_inference_flag
        == "ALLOW_STORED_ONLY"
    )
    assert match_field_metadata_rule("race_odds.win").train_inference_flag == "BLOCK"
    assert match_field_metadata_rule("horses[0].result").train_inference_flag == "BLOCK"
    assert match_field_metadata_rule("horses[0].payout").train_inference_flag == "BLOCK"
    assert (
        match_field_metadata_rule("snapshot_meta.replay_status").train_inference_flag
        == "META_ONLY"
    )
    assert (
        match_field_metadata_rule("source_field_tags.summary").train_inference_flag
        == "META_ONLY"
    )


def test_csv_template_rows_match_declared_rule_registry():
    template_path = (
        Path(__file__).resolve().parents[3] / CANONICAL_STORAGE_RELATIVE_PATH
    )
    with template_path.open(encoding=CANONICAL_STORAGE_ENCODING, newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert tuple(rows[0].keys()) == ALL_COLUMNS
    assert csv_header() == ",".join(ALL_COLUMNS)
    assert rows == list(canonical_field_metadata_rows())
