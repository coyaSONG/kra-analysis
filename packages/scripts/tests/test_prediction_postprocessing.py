from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.final_race_inference_schema import normalize_final_race_inference_payload
from shared.prediction_postprocessing import postprocess_prediction_candidates


@pytest.mark.parametrize(
    ("payload", "normalized_payload", "expected_source_field", "expected_top3"),
    [
        (
            {
                "selected_horses": [
                    {"chulNo": 8, "hrName": "선두후보"},
                    {"chulNo": "3", "hrName": "추입후보"},
                    {"chulNo": 1.0, "hrName": "복병"},
                ]
            },
            None,
            "selected_horses",
            [8, 3, 1],
        ),
        (
            {
                "predicted": [6, "2", 5],
            },
            None,
            "predicted",
            [6, 2, 5],
        ),
        (
            {
                "prediction": [
                    {"horse_no": "7", "horse_name": "주도마"},
                    {"horseNo": 4, "name": "추격마"},
                    {"number": 9, "hrName": "막판승부"},
                ]
            },
            None,
            "prediction",
            [7, 4, 9],
        ),
        (
            {
                "trifecta_picks": {
                    "primary": [3, 1, 2],
                }
            },
            None,
            "trifecta_picks.primary",
            [3, 1, 2],
        ),
        (
            {
                "primary_scores": [
                    {"chulNo": 4, "score": 0.83, "hrName": "강축"},
                    {"chulNo": 1, "score": 0.69, "hrName": "대항"},
                    {"chulNo": 6, "score": 0.51, "hrName": "복병"},
                ]
            },
            None,
            "primary_scores",
            [4, 1, 6],
        ),
        (
            {
                "predictions": [
                    {"chulNo": 5, "win_probability": 0.78, "hrName": "주력"},
                    {"chulNo": 2, "win_probability": 0.63, "hrName": "보조"},
                    {"chulNo": 9, "win_probability": 0.47, "hrName": "복병"},
                ]
            },
            None,
            "predictions",
            [5, 2, 9],
        ),
        (
            {},
            normalize_final_race_inference_payload(
                {
                    "fallback_ranking": [
                        {"rank": 1, "chulNo": 9, "source": "alternative_ranking_v1"},
                        {"rank": 2, "chulNo": 3, "source": "alternative_ranking_v1"},
                        {"rank": 3, "chulNo": 5, "source": "alternative_ranking_v1"},
                    ]
                }
            ),
            "normalized.selected_horses",
            [9, 3, 5],
        ),
    ],
)
def test_postprocess_prediction_candidates_returns_three_unique_horses_for_supported_normal_inputs(
    payload: dict[str, object],
    normalized_payload: dict[str, object] | None,
    expected_source_field: str,
    expected_top3: list[int],
) -> None:
    report = postprocess_prediction_candidates(
        payload,
        normalized_payload=normalized_payload,
    )

    assert report["valid"] is True
    assert report["source_field"] == expected_source_field
    assert report["raw_candidate_count"] == 3
    assert report["normalized_candidate_count"] == 3
    assert [row["chulNo"] for row in report["normalized_candidates"]] == expected_top3
    assert len({row["chulNo"] for row in report["normalized_candidates"]}) == 3
    assert report["issue_codes"] == []


def test_postprocess_prediction_candidates_accepts_exact_three_unique_horses() -> None:
    report = postprocess_prediction_candidates(
        {
            "selected_horses": [
                {"chulNo": "1", "hrName": "에이스"},
                {"chulNo": 2, "hrName": "챌린저"},
                {"chulNo": 3.0, "hrName": "피니셔"},
            ]
        }
    )

    assert report["valid"] is True
    assert report["source_field"] == "selected_horses"
    assert report["raw_candidate_count"] == 3
    assert report["normalized_candidate_count"] == 3
    assert report["normalized_candidates"] == [
        {
            "rank": 1,
            "chulNo": 1,
            "score": None,
            "hrName": "에이스",
            "source_field": "selected_horses",
            "raw_index": 1,
        },
        {
            "rank": 2,
            "chulNo": 2,
            "score": None,
            "hrName": "챌린저",
            "source_field": "selected_horses",
            "raw_index": 2,
        },
        {
            "rank": 3,
            "chulNo": 3,
            "score": None,
            "hrName": "피니셔",
            "source_field": "selected_horses",
            "raw_index": 3,
        },
    ]
    assert report["issue_codes"] == []


def test_postprocess_prediction_candidates_merges_duplicate_horse_numbers_by_score_priority() -> (
    None
):
    report = postprocess_prediction_candidates(
        {
            "selected_horses": [
                {"chulNo": 2, "hrName": "선행주자"},
                {"chulNo": 1, "hrName": "초기선택"},
                {"chulNo": 1, "hrName": "최종선택"},
                {"chulNo": 3, "hrName": "추입마"},
            ],
            "predictions": [
                {"chulNo": 2, "win_probability": 0.61},
                {"chulNo": 1, "win_probability": 0.64},
                {"chulNo": 1, "win_probability": 0.68},
                {"chulNo": 3, "win_probability": 0.57},
            ],
        }
    )

    assert report["valid"] is True
    assert report["source_field"] == "selected_horses"
    assert report["raw_candidate_count"] == 4
    assert report["normalized_candidate_count"] == 3
    assert report["normalized_candidates"] == [
        {
            "rank": 1,
            "chulNo": 1,
            "score": 0.68,
            "hrName": "초기선택",
            "source_field": "selected_horses",
            "raw_index": 2,
        },
        {
            "rank": 2,
            "chulNo": 2,
            "score": 0.61,
            "hrName": "선행주자",
            "source_field": "selected_horses",
            "raw_index": 1,
        },
        {
            "rank": 3,
            "chulNo": 3,
            "score": 0.57,
            "hrName": "추입마",
            "source_field": "selected_horses",
            "raw_index": 4,
        },
    ]
    assert report["issue_codes"] == []


def test_postprocess_prediction_candidates_trims_to_top_three_by_score_priority() -> (
    None
):
    report = postprocess_prediction_candidates(
        {
            "selected_horses": [
                {"chulNo": 2, "hrName": "차순위"},
                {"chulNo": 5, "hrName": "백업"},
                {"chulNo": 1, "hrName": "최우선"},
                {"chulNo": 4, "hrName": "탈락후보"},
            ],
            "predictions": [
                {"chulNo": 2, "win_probability": 0.61},
                {"chulNo": 5, "win_probability": 0.52},
                {"chulNo": 1, "win_probability": 0.73},
                {"chulNo": 4, "win_probability": 0.18},
            ],
        }
    )

    assert report["valid"] is True
    assert report["raw_candidate_count"] == 4
    assert report["normalized_candidate_count"] == 3
    assert report["normalized_candidates"] == [
        {
            "rank": 1,
            "chulNo": 1,
            "score": 0.73,
            "hrName": "최우선",
            "source_field": "selected_horses",
            "raw_index": 3,
        },
        {
            "rank": 2,
            "chulNo": 2,
            "score": 0.61,
            "hrName": "차순위",
            "source_field": "selected_horses",
            "raw_index": 1,
        },
        {
            "rank": 3,
            "chulNo": 5,
            "score": 0.52,
            "hrName": "백업",
            "source_field": "selected_horses",
            "raw_index": 2,
        },
    ]
    assert report["issue_codes"] == []


def test_postprocess_prediction_candidates_uses_tie_break_order_for_top_three_cutoff() -> (
    None
):
    report = postprocess_prediction_candidates(
        {
            "selected_horses": [
                {"chulNo": 7, "hrName": "선행동점"},
                {"chulNo": 4, "hrName": "중간동점"},
                {"chulNo": 9, "hrName": "후행동점"},
                {"chulNo": 2, "hrName": "탈락동점"},
            ],
            "predictions": [
                {"chulNo": 7, "win_probability": 0.41},
                {"chulNo": 4, "win_probability": 0.41},
                {"chulNo": 9, "win_probability": 0.41},
                {"chulNo": 2, "win_probability": 0.41},
            ],
        }
    )

    assert report["valid"] is True
    assert [row["chulNo"] for row in report["normalized_candidates"]] == [7, 4, 9]
    assert [row["raw_index"] for row in report["normalized_candidates"]] == [1, 2, 3]
    assert report["issue_codes"] == []


def test_postprocess_prediction_candidates_keeps_invalid_format_and_count_errors() -> (
    None
):
    report = postprocess_prediction_candidates(
        {
            "predicted": [1, "1", "3번", 0],
        }
    )

    assert report["valid"] is False
    assert report["source_field"] == "predicted"
    assert report["raw_candidate_count"] == 4
    assert report["normalized_candidate_count"] == 1
    assert report["issue_codes"] == [
        "invalid_horse_number_format",
        "invalid_horse_number_format",
        "prediction_count_not_three",
    ]


def test_postprocess_prediction_candidates_supplements_unique_shortage_by_score_priority() -> (
    None
):
    report = postprocess_prediction_candidates(
        {
            "selected_horses": [
                {"chulNo": 4, "hrName": "에이스"},
                {"chulNo": 4, "hrName": "중복에이스"},
                {"chulNo": 1, "hrName": "대항마"},
            ],
            "predictions": [
                {"chulNo": 4, "hrName": "에이스", "win_probability": 0.66},
                {"chulNo": 1, "hrName": "대항마", "win_probability": 0.52},
                {"chulNo": 6, "hrName": "보충후보", "win_probability": 0.44},
                {"chulNo": 3, "hrName": "차순위후보", "win_probability": 0.31},
            ],
        }
    )

    assert report["valid"] is True
    assert report["source_field"] == "selected_horses"
    assert report["raw_candidate_count"] == 3
    assert report["normalized_candidate_count"] == 3
    assert report["normalized_candidates"] == [
        {
            "rank": 1,
            "chulNo": 4,
            "score": 0.66,
            "hrName": "에이스",
            "source_field": "selected_horses",
            "raw_index": 1,
        },
        {
            "rank": 2,
            "chulNo": 1,
            "score": 0.52,
            "hrName": "대항마",
            "source_field": "selected_horses",
            "raw_index": 3,
        },
        {
            "rank": 3,
            "chulNo": 6,
            "score": 0.44,
            "hrName": "보충후보",
            "source_field": "raw.predictions",
            "raw_index": 3,
        },
    ]
    assert report["issue_codes"] == []


def test_postprocess_prediction_candidates_uses_normalized_payload_when_raw_list_missing() -> (
    None
):
    normalized = normalize_final_race_inference_payload(
        {
            "fallback_ranking": [
                {"rank": 1, "chulNo": 9, "source": "alternative_ranking_v1"},
                {"rank": 2, "chulNo": 3, "source": "alternative_ranking_v1"},
                {"rank": 3, "chulNo": 5, "source": "alternative_ranking_v1"},
            ]
        }
    )

    report = postprocess_prediction_candidates({}, normalized_payload=normalized)

    assert report["valid"] is True
    assert report["source_field"] == "normalized.selected_horses"
    assert report["normalized_candidate_count"] == 3
    assert [row["chulNo"] for row in report["normalized_candidates"]] == [9, 3, 5]
    assert [row["score"] for row in report["normalized_candidates"]] == [
        None,
        None,
        None,
    ]


def test_postprocess_prediction_candidates_filters_horses_outside_race_card_and_backfills_scores() -> (
    None
):
    report = postprocess_prediction_candidates(
        {
            "selected_horses": [
                {"chulNo": 4, "hrName": "에이스"},
                {"chulNo": 99, "hrName": "유령마"},
                {"chulNo": 1, "hrName": "캐논황후"},
                {"chulNo": 6, "hrName": "으뜸천하"},
            ],
            "predictions": [
                {"chulNo": 4, "hrName": "에이스", "win_probability": 0.32},
                {"chulNo": 1, "hrName": "캐논황후", "win_probability": 0.25},
                {"chulNo": 6, "hrName": "으뜸천하", "win_probability": 0.18},
            ],
        },
        valid_chul_nos=[4, 1, 6],
    )

    assert report["valid"] is False
    assert report["normalized_candidate_count"] == 3
    assert report["normalized_candidates"] == [
        {
            "rank": 1,
            "chulNo": 4,
            "score": 0.32,
            "hrName": "에이스",
            "source_field": "selected_horses",
            "raw_index": 1,
        },
        {
            "rank": 2,
            "chulNo": 1,
            "score": 0.25,
            "hrName": "캐논황후",
            "source_field": "selected_horses",
            "raw_index": 3,
        },
        {
            "rank": 3,
            "chulNo": 6,
            "score": 0.18,
            "hrName": "으뜸천하",
            "source_field": "selected_horses",
            "raw_index": 4,
        },
    ]
    assert report["issue_codes"] == ["horse_number_not_in_race_card"]


@pytest.mark.parametrize(
    (
        "payload",
        "normalized_payload",
        "valid_chul_nos",
        "expected_source_field",
        "expected_chul_nos",
        "expected_issue_codes",
    ),
    [
        (
            {
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
            None,
            None,
            "selected_horses",
            {4, 7, 2},
            [
                "invalid_horse_number_format",
                "invalid_horse_number_format",
            ],
        ),
        (
            {
                "predicted": [8, None, 8, 4],
                "model_scores": {
                    "8": 0.71,
                    "4": 0.63,
                    "2": 0.59,
                    "7": 0.41,
                },
            },
            None,
            [8, 4, 2],
            "predicted",
            {8, 4, 2},
            ["invalid_horse_number_format"],
        ),
        (
            {
                "selected_horses": {"unexpected": True},
                "predicted": ["5", 5],
            },
            normalize_final_race_inference_payload(
                {
                    "fallback_ranking": [
                        {"rank": 1, "chulNo": 9, "source": "alternative_ranking_v1"},
                        {"rank": 2, "chulNo": 2, "source": "alternative_ranking_v1"},
                        {"rank": 3, "chulNo": 7, "source": "alternative_ranking_v1"},
                    ]
                }
            ),
            None,
            "predicted",
            {5, 9, 2},
            ["invalid_candidate_source_type"],
        ),
    ],
)
def test_postprocess_prediction_candidates_returns_three_unique_horses_for_abnormal_inputs_when_supplement_paths_exist(
    payload: dict[str, object],
    normalized_payload: dict[str, object] | None,
    valid_chul_nos: list[int] | None,
    expected_source_field: str,
    expected_chul_nos: set[int],
    expected_issue_codes: list[str],
) -> None:
    report = postprocess_prediction_candidates(
        payload,
        normalized_payload=normalized_payload,
        valid_chul_nos=valid_chul_nos,
    )

    normalized_chul_nos = [row["chulNo"] for row in report["normalized_candidates"]]

    assert report["source_field"] == expected_source_field
    assert report["normalized_candidate_count"] == 3
    assert len(normalized_chul_nos) == 3
    assert len(set(normalized_chul_nos)) == 3
    assert set(normalized_chul_nos) == expected_chul_nos
    assert report["issue_codes"] == expected_issue_codes
