"""Tests for the race-level Laya data-capacity audit."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import single_combo_laya_data_capacity_audit as audit  # noqa: E402


def _healthy_cache() -> dict[str, object]:
    return {
        "dataset": "fixture",
        "rows": [
            {
                "race_id": "20250101_1_1",
                "race_date": "20250101",
                "chulNo": chul_no,
                "target": int(chul_no <= 3),
                "rating": float(chul_no),
                "optional": math.nan if chul_no == 4 else 1.0,
            }
            for chul_no in range(1, 5)
        ]
        + [
            {
                "race_id": "20250102_1_1",
                "race_date": "20250102",
                "chulNo": chul_no,
                "target": int(chul_no <= 3),
                "rating": float(chul_no + 10),
                "optional": None,
            }
            for chul_no in range(1, 5)
        ],
        "answers": {
            "20250101_1_1": [1, 2, 3],
            "20250102_1_1": [3, 2, 1],
        },
    }


def test_audit_row_cache_reports_independent_race_capacity() -> None:
    result = audit.audit_row_cache(
        _healthy_cache(),
        projected_row_counts=(80, 160),
        target_unique_races=20,
    )

    assert result["status"] == "passed"
    assert result["counts_as_70_percent_evidence"] is False
    assert result["grain"] == {
        "intended_row_grain": "one_active_runner_per_race",
        "independent_supervised_grain": "one_race_choice",
        "row_count": 8,
        "unique_race_count": 2,
        "usable_unique_race_count": 2,
        "mean_rows_per_race": 4.0,
        "min_field_size": 4,
        "max_field_size": 4,
    }
    assert result["date_coverage"]["min_race_date"] == "20250101"
    assert result["date_coverage"]["max_race_date"] == "20250102"
    assert result["projections"][0]["projected_unique_race_count"] == 20
    assert result["projections"][0]["meets_target_unique_races"] is True


def test_audit_row_cache_profiles_missing_features() -> None:
    result = audit.audit_row_cache(_healthy_cache())

    missingness = result["missingness"]
    assert missingness["feature_count"] == 2
    assert missingness["feature_cell_count"] == 16
    assert missingness["missing_feature_cell_count"] == 5
    assert missingness["missing_feature_cell_rate"] == 0.3125
    assert missingness["fully_missing_feature_count"] == 0
    assert missingness["features_at_or_above_20pct_missing"] == [
        {"feature": "optional", "missing_rate": 0.625}
    ]


def test_audit_row_cache_fails_duplicate_and_invalid_label() -> None:
    row_cache = _healthy_cache()
    rows = row_cache["rows"]
    assert isinstance(rows, list)
    rows.append(dict(rows[0]))
    answers = row_cache["answers"]
    assert isinstance(answers, dict)
    answers["20250102_1_1"] = [1, 1, 4]

    result = audit.audit_row_cache(row_cache)

    assert result["status"] == "failed"
    assert result["duplicate_quality"]["duplicate_entry_key_count"] == 1
    assert result["duplicate_quality"]["duplicate_row_excess_count"] == 1
    assert result["label_quality"]["invalid_answer_count"] == 1
    assert result["quality_failures"]["duplicate_entry_keys"] == 1
    assert result["quality_failures"]["invalid_answers"] == 1
    assert (
        result["recommended_next_action"]
        == "repair_row_cache_quality_failures_before_laya_export"
    )


def test_audit_row_cache_rejects_invalid_shapes() -> None:
    with pytest.raises(ValueError, match="rows must be a list"):
        audit.audit_row_cache({"rows": {}, "answers": {}})

    with pytest.raises(ValueError, match="answers must be a dictionary"):
        audit.audit_row_cache({"rows": [], "answers": []})

    with pytest.raises(ValueError, match="target_unique_races must be positive"):
        audit.audit_row_cache(_healthy_cache(), target_unique_races=0)
