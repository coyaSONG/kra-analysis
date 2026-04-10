from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.model_score_status_schema import (  # noqa: E402
    ALL_COLUMNS,
    CANONICAL_STORAGE_ENCODING,
    CANONICAL_STORAGE_RELATIVE_PATH,
    REQUIRED_COLUMNS,
    RULE_SCHEMA_VERSION,
    STATUS_CLASSES,
    STATUS_CODES,
    STATUS_SPEC_BY_CODE,
    csv_header,
)


def test_rule_schema_version_is_fixed():
    assert RULE_SCHEMA_VERSION == "model-score-status-rules-v1"


def test_required_columns_cover_scoring_contract():
    required = set(REQUIRED_COLUMNS)
    assert {
        "precedence",
        "status_code",
        "status_class",
        "status_reason",
        "trigger_condition",
        "json_ok",
        "deferred",
        "coverage_included",
        "score_aggregated",
        "fallback_required",
        "fallback_action",
    } <= required


def test_explicit_status_enums_remain_fixed():
    assert STATUS_CLASSES == ("scored", "deferred", "missing", "failed")
    assert STATUS_CODES == (
        "FAIL_ACTUAL_TOP3_MISSING",
        "FAIL_ACTUAL_TOP3_INVALID",
        "FAIL_PREDICTION_PAYLOAD_MISSING",
        "MISSING_PREDICTED_TOP3",
        "FAIL_PREDICTED_TOP3_INVALID",
        "MISSING_CONFIDENCE",
        "FAIL_CONFIDENCE_INVALID",
        "DEFERRED_LOW_CONFIDENCE",
        "SCORED_OK",
    )


def test_status_spec_exposes_race_status_contract():
    scored = STATUS_SPEC_BY_CODE["SCORED_OK"]
    deferred = STATUS_SPEC_BY_CODE["DEFERRED_LOW_CONFIDENCE"]

    assert scored.race_status_payload() == {
        "status_code": "SCORED_OK",
        "status_class": "scored",
        "status_reason": "예측과 confidence가 모두 유효하며 정상 집계 대상이다.",
        "fallback_required": False,
        "fallback_action": "set_match 와 correct_count 를 정상 집계",
    }
    assert deferred.fallback_required is True
    assert deferred.deferred is True


def test_csv_template_header_matches_declared_column_order():
    template_path = (
        Path(__file__).resolve().parents[3] / CANONICAL_STORAGE_RELATIVE_PATH
    )
    with template_path.open(encoding=CANONICAL_STORAGE_ENCODING, newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)

    assert tuple(header) == ALL_COLUMNS
    assert ",".join(header) == csv_header()


def test_rule_table_covers_failure_missing_and_deferred_cases():
    template_path = (
        Path(__file__).resolve().parents[3] / CANONICAL_STORAGE_RELATIVE_PATH
    )
    with template_path.open(encoding=CANONICAL_STORAGE_ENCODING, newline="") as handle:
        rows = list(csv.DictReader(handle))

    codes = {row["status_code"] for row in rows}
    assert set(STATUS_CODES) == codes
    assert rows
    assert [int(row["precedence"]) for row in rows] == sorted(
        int(row["precedence"]) for row in rows
    )
    assert all(row["rule_schema_version"] == RULE_SCHEMA_VERSION for row in rows)
