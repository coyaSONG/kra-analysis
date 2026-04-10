from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "autoresearch"))

from prepare import compute_score  # noqa: E402
from shared.model_score_status_schema import STATUS_SPEC_BY_CODE  # noqa: E402

EXPECTED_SCORE_KEYS = {
    "json_ok",
    "deferred",
    "race_status",
    "status_code",
    "status_class",
    "status_reason",
    "fallback_required",
    "fallback_action",
    "normalized_confidence",
    "coverage_included",
    "score_aggregated",
    "set_match",
    "correct_count",
}

EXPECTED_RACE_STATUS_KEYS = [
    "status_code",
    "status_class",
    "status_reason",
    "fallback_required",
    "fallback_action",
]


def _assert_score_contract(
    score: dict,
    *,
    expected_status_code: str,
    expected_normalized_confidence: float | None,
    expected_set_match: float,
    expected_correct_count: int,
) -> None:
    spec = STATUS_SPEC_BY_CODE[expected_status_code]

    assert set(score) == EXPECTED_SCORE_KEYS
    assert list(score["race_status"].keys()) == EXPECTED_RACE_STATUS_KEYS

    assert score["race_status"] == spec.race_status_payload()
    assert score["status_code"] == spec.status_code
    assert score["status_class"] == spec.status_class
    assert score["status_reason"] == spec.status_reason
    assert score["fallback_required"] == spec.fallback_required
    assert score["fallback_action"] == spec.fallback_action

    assert score["json_ok"] == spec.json_ok
    assert score["deferred"] == spec.deferred
    assert score["coverage_included"] == spec.coverage_included
    assert score["score_aggregated"] == spec.score_aggregated
    assert score["normalized_confidence"] == expected_normalized_confidence
    assert score["set_match"] == pytest.approx(expected_set_match)
    assert score["correct_count"] == expected_correct_count


@pytest.mark.parametrize(
    (
        "case_name",
        "prediction",
        "actual",
        "expected_status_code",
        "expected_confidence",
        "expected_set_match",
        "expected_correct_count",
    ),
    [
        (
            "normal_scored",
            {"predicted": [1, 2, 3], "confidence": 0.91},
            [1, 2, 3],
            "SCORED_OK",
            0.91,
            1.0,
            3,
        ),
        (
            "failed_payload_missing",
            None,
            [1, 2, 3],
            "FAIL_PREDICTION_PAYLOAD_MISSING",
            None,
            0.0,
            0,
        ),
        (
            "missing_confidence",
            {"predicted": [1, 2, 3]},
            [1, 2, 3],
            "MISSING_CONFIDENCE",
            None,
            0.0,
            0,
        ),
        (
            "deferred_low_confidence",
            {"predicted": [1, 2, 3], "confidence": 0.2},
            [1, 3, 5],
            "DEFERRED_LOW_CONFIDENCE",
            0.2,
            2 / 3,
            2,
        ),
        (
            "fallback_required_invalid_prediction",
            {"predicted": [1, 1, 3], "confidence": 0.88},
            [1, 2, 3],
            "FAIL_PREDICTED_TOP3_INVALID",
            None,
            0.0,
            0,
        ),
    ],
)
def test_compute_score_returns_canonical_contract_for_each_status_family(
    case_name: str,
    prediction: dict | None,
    actual: list[int],
    expected_status_code: str,
    expected_confidence: float | None,
    expected_set_match: float,
    expected_correct_count: int,
) -> None:
    score = compute_score(prediction, actual)

    _assert_score_contract(
        score,
        expected_status_code=expected_status_code,
        expected_normalized_confidence=expected_confidence,
        expected_set_match=expected_set_match,
        expected_correct_count=expected_correct_count,
    )

    if case_name == "fallback_required_invalid_prediction":
        assert score["fallback_required"] is True
        assert (
            score["race_status"]["fallback_action"]
            == "set_match=0, correct_count=0 으로 고정"
        )
