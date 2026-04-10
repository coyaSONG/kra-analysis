from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.final_race_inference_schema import normalize_final_race_inference_payload


@dataclass(frozen=True, slots=True)
class PredictionPostprocessingRegressionCase:
    name: str
    payload: dict[str, Any]
    normalized_payload: dict[str, Any] | None
    valid_chul_nos: tuple[int, ...] | None
    expected_source_field: str
    expected_postprocess_top3: tuple[int, ...]
    expected_postprocess_issue_codes: tuple[str, ...]
    expected_guard_final_predicted: tuple[int, int, int]
    expected_guard_accepted: bool
    expected_guard_repaired: bool
    expected_guard_repair_action_codes: tuple[str, ...]


PREDICTION_POSTPROCESSING_REGRESSION_CASES = (
    PredictionPostprocessingRegressionCase(
        name="normal_selected_horses_exact_three",
        payload={
            "selected_horses": [
                {"chulNo": 8, "hrName": "선두후보"},
                {"chulNo": "3", "hrName": "추입후보"},
                {"chulNo": 1.0, "hrName": "복병"},
            ]
        },
        normalized_payload=None,
        valid_chul_nos=None,
        expected_source_field="selected_horses",
        expected_postprocess_top3=(8, 3, 1),
        expected_postprocess_issue_codes=(),
        expected_guard_final_predicted=(8, 3, 1),
        expected_guard_accepted=True,
        expected_guard_repaired=False,
        expected_guard_repair_action_codes=(),
    ),
    PredictionPostprocessingRegressionCase(
        name="abnormal_duplicate_and_invalid_are_supplemented_from_primary_scores",
        payload={
            "selected_horses": [
                {"chulNo": 4, "hrName": "에이스"},
                {"chulNo": 4, "hrName": "중복에이스"},
                {"chulNo": None, "hrName": "번호결측"},
                {"horseNo": "", "name": "빈번호"},
            ],
            "primary_scores": [
                {"chulNo": 4, "score": 0.81, "hrName": "에이스"},
                {"chulNo": 7, "score": 0.64, "hrName": "보충후보1"},
                {"chulNo": 2, "score": 0.61, "hrName": "보충후보2"},
                {"chulNo": 9, "score": 0.12, "hrName": "탈락후보"},
            ],
        },
        normalized_payload=None,
        valid_chul_nos=None,
        expected_source_field="selected_horses",
        expected_postprocess_top3=(4, 7, 2),
        expected_postprocess_issue_codes=(
            "invalid_horse_number_format",
            "invalid_horse_number_format",
        ),
        expected_guard_final_predicted=(4, 7, 2),
        expected_guard_accepted=True,
        expected_guard_repaired=True,
        expected_guard_repair_action_codes=(
            "deduped_or_trimmed_candidates",
            "discarded_invalid_format_candidates",
        ),
    ),
    PredictionPostprocessingRegressionCase(
        name="abnormal_duplicates_are_completed_from_model_scores",
        payload={
            "predicted": [8, None, 8, 4],
            "model_scores": {
                "8": 0.71,
                "4": 0.63,
                "2": 0.59,
                "7": 0.41,
            },
        },
        normalized_payload=None,
        valid_chul_nos=(8, 4, 2),
        expected_source_field="predicted",
        expected_postprocess_top3=(8, 4, 2),
        expected_postprocess_issue_codes=("invalid_horse_number_format",),
        expected_guard_final_predicted=(8, 4, 2),
        expected_guard_accepted=True,
        expected_guard_repaired=True,
        expected_guard_repair_action_codes=(
            "deduped_or_trimmed_candidates",
            "discarded_invalid_format_candidates",
        ),
    ),
    PredictionPostprocessingRegressionCase(
        name="abnormal_missing_slot_is_filled_from_race_card",
        payload={
            "selected_horses": [
                {"chulNo": 1},
                {"chulNo": 0},
                {"chulNo": 2},
            ]
        },
        normalized_payload=None,
        valid_chul_nos=(1, 2, 3, 4),
        expected_source_field="selected_horses",
        expected_postprocess_top3=(1, 2),
        expected_postprocess_issue_codes=(
            "invalid_horse_number_format",
            "prediction_count_not_three",
        ),
        expected_guard_final_predicted=(1, 2, 3),
        expected_guard_accepted=True,
        expected_guard_repaired=True,
        expected_guard_repair_action_codes=(
            "deduped_or_trimmed_candidates",
            "discarded_invalid_format_candidates",
            "filled_from_race_card",
        ),
    ),
    PredictionPostprocessingRegressionCase(
        name="normalized_fallback_ranking_keeps_three_unique_horses",
        payload={},
        normalized_payload=normalize_final_race_inference_payload(
            {
                "fallback_ranking": [
                    {"rank": 1, "chulNo": 9, "source": "alternative_ranking_v1"},
                    {"rank": 2, "chulNo": 3, "source": "alternative_ranking_v1"},
                    {"rank": 3, "chulNo": 5, "source": "alternative_ranking_v1"},
                ]
            }
        ),
        valid_chul_nos=None,
        expected_source_field="normalized.selected_horses",
        expected_postprocess_top3=(9, 3, 5),
        expected_postprocess_issue_codes=(),
        expected_guard_final_predicted=(9, 3, 5),
        expected_guard_accepted=True,
        expected_guard_repaired=False,
        expected_guard_repair_action_codes=(),
    ),
)
