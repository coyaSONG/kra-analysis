from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autoresearch.prepare import build_coverage_validation_result


def test_build_coverage_validation_result_returns_structured_failure_for_missing_items() -> (
    None
):
    races = [
        {"race_id": "race-1"},
        {"race_id": "race-2"},
        {"race_id": "race-3"},
    ]
    results = [
        {
            "score_aggregated": True,
            "status_code": "SCORED_OK",
            "status_class": "scored",
            "status_reason": "정상 집계",
            "fallback_action": None,
        },
        {
            "score_aggregated": False,
            "status_code": "DEFERRED_LOW_CONFIDENCE",
            "status_class": "deferred",
            "status_reason": "confidence 가 낮아 보류",
            "fallback_action": "재예측 또는 안전 기본값 사용",
        },
        {
            "score_aggregated": False,
            "status_code": "MISSING_PREDICTED_TOP3",
            "status_class": "missing",
            "status_reason": "predicted_top3 누락",
            "fallback_action": "set_match=0, correct_count=0 으로 고정",
        },
    ]

    validation = build_coverage_validation_result(results, races=races)

    assert validation["passed"] is False
    assert validation["missing_count"] == 2
    assert validation["covered_count"] == 1
    assert abs(validation["coverage_pct"] - (100 / 3)) < 1e-9
    assert validation["failure"]["reason_code"] == "COVERAGE_MISSING_ITEMS"
    assert validation["failure"]["missing_count"] == 2
    assert validation["failure"]["missing_items"] == [
        {
            "result_index": 1,
            "race_id": "race-2",
            "status_code": "DEFERRED_LOW_CONFIDENCE",
            "status_class": "deferred",
            "status_reason": "confidence 가 낮아 보류",
            "fallback_action": "재예측 또는 안전 기본값 사용",
        },
        {
            "result_index": 2,
            "race_id": "race-3",
            "status_code": "MISSING_PREDICTED_TOP3",
            "status_class": "missing",
            "status_reason": "predicted_top3 누락",
            "fallback_action": "set_match=0, correct_count=0 으로 고정",
        },
    ]


def test_build_coverage_validation_result_passes_when_no_missing_items() -> None:
    validation = build_coverage_validation_result(
        [
            {
                "score_aggregated": True,
                "status_code": "SCORED_OK",
                "status_class": "scored",
                "status_reason": "정상 집계",
                "fallback_action": None,
            }
        ]
    )

    assert validation["passed"] is True
    assert validation["missing_count"] == 0
    assert validation["missing_items"] == []
    assert "failure" not in validation
