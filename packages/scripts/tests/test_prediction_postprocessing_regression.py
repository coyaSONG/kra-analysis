from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixtures.prediction_postprocessing_cases import (
    PREDICTION_POSTPROCESSING_REGRESSION_CASES,
    PredictionPostprocessingRegressionCase,
)
from shared.prediction_output_guard import guard_prediction_output
from shared.prediction_postprocessing import postprocess_prediction_candidates


@pytest.mark.parametrize(
    "case",
    PREDICTION_POSTPROCESSING_REGRESSION_CASES,
    ids=lambda case: case.name,
)
def test_postprocess_prediction_candidates_regression_cases_keep_expected_candidates(
    case: PredictionPostprocessingRegressionCase,
) -> None:
    report = postprocess_prediction_candidates(
        case.payload,
        normalized_payload=case.normalized_payload,
        valid_chul_nos=case.valid_chul_nos,
    )

    normalized_top3 = tuple(row["chulNo"] for row in report["normalized_candidates"])

    assert report["source_field"] == case.expected_source_field
    assert normalized_top3 == case.expected_postprocess_top3
    assert len(normalized_top3) == len(set(normalized_top3))
    assert tuple(report["issue_codes"]) == case.expected_postprocess_issue_codes


@pytest.mark.parametrize(
    "case",
    PREDICTION_POSTPROCESSING_REGRESSION_CASES,
    ids=lambda case: case.name,
)
def test_guard_prediction_output_regression_cases_always_emit_three_unique_horses(
    case: PredictionPostprocessingRegressionCase,
) -> None:
    report = guard_prediction_output(
        case.payload,
        normalized_payload=case.normalized_payload,
        valid_chul_nos=case.valid_chul_nos,
    )

    assert report["accepted"] is case.expected_guard_accepted
    assert report["repaired"] is case.expected_guard_repaired
    assert (
        tuple(report["repair_action_codes"]) == case.expected_guard_repair_action_codes
    )
    assert tuple(report["final_predicted"]) == case.expected_guard_final_predicted
    assert len(report["final_predicted"]) == 3
    assert len(set(report["final_predicted"])) == 3
    assert [row["chulNo"] for row in report["final_selected_horses"]] == list(
        case.expected_guard_final_predicted
    )
