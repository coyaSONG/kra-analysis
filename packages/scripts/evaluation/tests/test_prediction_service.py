import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.prediction_service import (
    build_prediction_prompt,
    finalize_prediction_payload,
    normalize_prediction_payload,
    parse_prediction_output,
)


def _race_data_with_horses(*horse_numbers: int) -> dict:
    return {
        "horses": [{"chulNo": horse_number} for horse_number in horse_numbers],
    }


def test_build_prediction_prompt_embeds_json_payload():
    prompt = build_prediction_prompt(
        "PROMPT",
        {"raceInfo": {"rcDate": "20240719"}, "horses": [{"chulNo": 1}]},
    )

    assert "PROMPT" in prompt
    assert '"chulNo": 1' in prompt
    assert "selected_horses" in prompt


def test_parse_prediction_output_normalizes_code_block():
    output = """```json
{"predicted":[1,2,3],"confidence":80}
```"""

    parsed = parse_prediction_output(output, 1.25)

    assert parsed is not None
    assert parsed["execution_time"] == 1.25
    assert parsed["schema_version"] == "final-race-inference-v1"
    assert parsed["predicted"] == [1, 2, 3]
    assert parsed["top3"] == [1, 2, 3]
    assert parsed["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert parsed["primary_scores"] == []
    assert parsed["fallback_ranking"] == []
    assert parsed["fallback_meta"] == {
        "available": False,
        "applied": False,
        "reason_code": None,
        "reason": None,
        "source": None,
        "details": None,
    }
    assert parsed["fallback_used"] is False
    assert parsed["fallback_reason_code"] is None
    assert parsed["fallback_reason"] is None
    assert parsed["prediction_output_format"] == {
        "version": "unordered-top3-unique-v1",
        "predicted_count": 3,
        "is_unique": True,
    }
    assert parsed["prediction_validation"] == {
        "valid": True,
        "source_field": "predicted",
        "raw_candidate_count": 3,
        "normalized_candidate_count": 3,
        "normalized_candidates": [
            {
                "rank": 1,
                "chulNo": 1,
                "score": None,
                "hrName": None,
                "source_field": "predicted",
                "raw_index": 1,
            },
            {
                "rank": 2,
                "chulNo": 2,
                "score": None,
                "hrName": None,
                "source_field": "predicted",
                "raw_index": 2,
            },
            {
                "rank": 3,
                "chulNo": 3,
                "score": None,
                "hrName": None,
                "source_field": "predicted",
                "raw_index": 3,
            },
        ],
        "issue_codes": [],
        "issues": [],
    }


def test_normalize_prediction_payload_preserves_selected_horses():
    normalized = normalize_prediction_payload(
        {"selected_horses": [{"chulNo": 9}], "confidence": 10}, execution_time=0.3
    )

    assert normalized["schema_version"] == "final-race-inference-v1"
    assert normalized["execution_time"] == 0.3
    assert normalized["predicted"] == [9]
    assert normalized["top3"] == [9]
    assert normalized["selected_horses"] == [{"chulNo": 9}]
    assert normalized["prediction_validation"]["valid"] is False
    assert normalized["prediction_validation"]["issue_codes"] == [
        "prediction_count_not_three"
    ]


def test_normalize_prediction_payload_includes_primary_scores_and_fallback_backup():
    normalized = normalize_prediction_payload(
        {
            "trifecta_picks": {"primary": [4, 1, 6], "backup": [4, 6, 1]},
            "predictions": [
                {"chulNo": 4, "hrName": "지리산", "win_probability": 0.32},
                {"chulNo": 1, "hrName": "캐논황후", "win_probability": 0.25},
                {"chulNo": 6, "hrName": "으뜸천하", "win_probability": 0.18},
            ],
            "confidence": 0.72,
            "reasoning": "race reasoning",
        },
        execution_time=0.8,
    )

    assert normalized["predicted"] == [4, 1, 6]
    assert normalized["top3"] == [4, 1, 6]
    assert normalized["primary_scores"] == [
        {"chulNo": 4, "score": 0.32, "hrName": "지리산", "source": "win_probability"},
        {"chulNo": 1, "score": 0.25, "hrName": "캐논황후", "source": "win_probability"},
        {"chulNo": 6, "score": 0.18, "hrName": "으뜸천하", "source": "win_probability"},
    ]
    assert [entry["chulNo"] for entry in normalized["fallback_ranking"]] == [4, 6, 1]
    assert normalized["fallback_meta"]["available"] is True
    assert normalized["fallback_meta"]["source"] == "trifecta_picks.backup"
    assert normalized["fallback_used"] is False
    assert normalized["prediction_validation"]["valid"] is True
    assert (
        normalized["prediction_validation"]["source_field"] == "trifecta_picks.primary"
    )


def test_normalize_prediction_payload_merges_fallback_when_primary_scores_are_incomplete():
    normalized = normalize_prediction_payload(
        {
            "predictions": [
                {"chulNo": 4, "hrName": "지리산", "win_probability": 0.32},
                {"chulNo": 1, "hrName": "캐논황후", "win_probability": "NaN"},
            ],
            "fallback_ranking": [
                {"rank": 1, "chulNo": 6, "source": "alternative_ranking_v1"},
                {"rank": 2, "chulNo": 4, "source": "alternative_ranking_v1"},
                {"rank": 3, "chulNo": 1, "source": "alternative_ranking_v1"},
            ],
        },
        execution_time=0.4,
    )

    assert normalized["predicted"] == [4, 6, 1]
    assert normalized["top3"] == [4, 6, 1]
    assert normalized["selected_horses"] == [
        {"chulNo": 4},
        {"chulNo": 6},
        {"chulNo": 1},
    ]
    assert normalized["primary_scores"] == [
        {"chulNo": 4, "score": 0.32, "hrName": "지리산", "source": "win_probability"},
    ]
    assert normalized["fallback_meta"]["applied"] is True
    assert normalized["fallback_meta"]["reason_code"] == "PRIMARY_SCORES_PARTIAL"
    assert normalized["fallback_meta"]["details"] == {
        "valid_primary_score_count": 1,
        "fallback_candidate_count": 3,
        "fallback_used_count": 2,
        "fallback_used_chul_nos": [6, 1],
    }
    assert normalized["fallback_used"] is True
    assert normalized["fallback_reason_code"] == "PRIMARY_SCORES_PARTIAL"
    assert normalized["prediction_validation"]["valid"] is True


def test_parse_prediction_output_accepts_duplicate_prediction_when_unique_top3_is_restored():
    duplicate_output = """```json
{"predicted":[1,1,2,3],"confidence":80}
```"""

    parsed = parse_prediction_output(duplicate_output, 1.0)

    assert parsed is not None
    assert parsed["predicted"] == [1, 2, 3]
    assert parsed["prediction_validation"]["valid"] is True
    assert [
        row["chulNo"]
        for row in parsed["prediction_validation"]["normalized_candidates"]
    ] == [
        1,
        2,
        3,
    ]


def test_parse_prediction_output_rejects_underfilled_prediction():
    underfilled_output = """```json
{"selected_horses":[{"chulNo":"1"},{"chulNo":"2"}],"confidence":80}
```"""

    assert parse_prediction_output(underfilled_output, 1.0) is None


def test_parse_prediction_output_accepts_underfilled_prediction_when_scores_fill_gap():
    output = """```json
{"selected_horses":[{"chulNo":1},{"chulNo":1},{"chulNo":2}],"predictions":[{"chulNo":1,"win_probability":0.81},{"chulNo":2,"win_probability":0.63},{"chulNo":3,"win_probability":0.41}],"confidence":80}
```"""

    parsed = parse_prediction_output(output, 1.0)

    assert parsed is not None
    assert parsed["predicted"] == [1, 2, 3]
    assert parsed["top3"] == [1, 2, 3]
    assert parsed["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert parsed["prediction_validation"]["valid"] is True
    assert [
        row["chulNo"]
        for row in parsed["prediction_validation"]["normalized_candidates"]
    ] == [
        1,
        2,
        3,
    ]


def test_parse_prediction_output_accepts_format_mismatch_when_race_card_fills_gap() -> (
    None
):
    output = """```json
{"selected_horses":[{"chulNo":1},{"chulNo":"bad"},{"chulNo":2}],"confidence":80}
```"""

    parsed = parse_prediction_output(
        output,
        1.0,
        race_data={"horses": [{"chulNo": 1}, {"chulNo": 2}, {"chulNo": 3}]},
    )

    assert parsed is not None
    assert parsed["predicted"] == [1, 2, 3]
    assert parsed["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert parsed["prediction_validation"]["valid"] is False
    assert parsed["prediction_validation"]["issue_codes"] == [
        "invalid_horse_number_format",
        "prediction_count_not_three",
    ]
    assert parsed["prediction_correction"]["accepted"] is True
    assert parsed["prediction_correction"]["repair_action_codes"] == [
        "deduped_or_trimmed_candidates",
        "discarded_invalid_format_candidates",
        "filled_from_race_card",
    ]


@pytest.mark.parametrize(
    ("prediction", "race_data", "expected_predicted", "expected_issue_codes"),
    [
        (
            {
                "selected_horses": [
                    {"chulNo": 1},
                    {"chulNo": 1},
                    {"chulNo": 2},
                    {"chulNo": 3},
                ],
                "confidence": 80,
            },
            _race_data_with_horses(1, 2, 3),
            [1, 2, 3],
            [],
        ),
        (
            {
                "selected_horses": [
                    {"chulNo": 1},
                    {"chulNo": 2},
                ],
                "predictions": [
                    {"chulNo": 1, "win_probability": 0.81},
                    {"chulNo": 2, "win_probability": 0.63},
                    {"chulNo": 3, "win_probability": 0.41},
                ],
                "confidence": 80,
            },
            _race_data_with_horses(1, 2, 3),
            [1, 2, 3],
            [],
        ),
        (
            {
                "selected_horses": [
                    {"chulNo": 4},
                    {"chulNo": 2},
                    {"chulNo": 5},
                    {"chulNo": 1},
                ],
                "predictions": [
                    {"chulNo": 4, "win_probability": 0.78},
                    {"chulNo": 2, "win_probability": 0.64},
                    {"chulNo": 5, "win_probability": 0.55},
                    {"chulNo": 1, "win_probability": 0.91},
                ],
                "confidence": 80,
            },
            _race_data_with_horses(1, 2, 4, 5),
            [1, 4, 2],
            [],
        ),
        (
            {
                "selected_horses": [
                    {"chulNo": 1},
                    {"chulNo": 0},
                    {"chulNo": "x"},
                    {"chulNo": 2},
                ],
                "predictions": [
                    {"chulNo": 1, "win_probability": 0.82},
                    {"chulNo": 2, "win_probability": 0.67},
                    {"chulNo": 3, "win_probability": 0.44},
                    {"chulNo": 99, "win_probability": 0.99},
                ],
                "confidence": 80,
            },
            _race_data_with_horses(1, 2, 3),
            [1, 2, 3],
            [
                "invalid_horse_number_format",
                "invalid_horse_number_format",
            ],
        ),
        (
            {
                "selected_horses": [
                    {"chulNo": 1},
                    {"chulNo": "bad"},
                    {"chulNo": 2},
                ],
                "confidence": 80,
            },
            _race_data_with_horses(1, 2, 3),
            [1, 2, 3],
            [
                "invalid_horse_number_format",
                "prediction_count_not_three",
            ],
        ),
        (
            {
                "selected_horses": [
                    {"chulNo": 5},
                    {"chulNo": 5},
                    {"chulNo": 0},
                    {"chulNo": 4},
                    {"chulNo": 3},
                    {"chulNo": 2},
                    {"chulNo": "bad"},
                ],
                "predictions": [
                    {"chulNo": 5, "win_probability": 0.95},
                    {"chulNo": 4, "win_probability": 0.89},
                    {"chulNo": 2, "win_probability": 0.84},
                    {"chulNo": 3, "win_probability": 0.35},
                ],
                "confidence": 80,
            },
            _race_data_with_horses(2, 3, 4, 5),
            [5, 4, 2],
            [
                "invalid_horse_number_format",
                "invalid_horse_number_format",
            ],
        ),
    ],
)
def test_normalize_prediction_payload_returns_exactly_three_unique_predictions_for_any_candidate_shape(
    prediction: dict,
    race_data: dict,
    expected_predicted: list[int],
    expected_issue_codes: list[str],
):
    normalized = normalize_prediction_payload(
        prediction,
        execution_time=0.5,
        race_data=race_data,
    )

    assert normalized["predicted"] == expected_predicted
    assert normalized["top3"] == expected_predicted
    assert normalized["selected_horses"] == [
        {"chulNo": chul_no} for chul_no in expected_predicted
    ]
    assert len(normalized["predicted"]) == 3
    assert len(set(normalized["predicted"])) == 3
    assert normalized["prediction_validation"]["normalized_candidate_count"] == 3
    assert [
        row["chulNo"]
        for row in normalized["prediction_validation"]["normalized_candidates"]
    ] == expected_predicted
    assert normalized["prediction_validation"]["issue_codes"] == expected_issue_codes


def test_parse_prediction_output_accepts_overfilled_prediction_when_top_three_is_trimmed() -> (
    None
):
    output = """```json
{"selected_horses":[{"chulNo":2},{"chulNo":5},{"chulNo":1},{"chulNo":4}],"predictions":[{"chulNo":2,"win_probability":0.61},{"chulNo":5,"win_probability":0.52},{"chulNo":1,"win_probability":0.73},{"chulNo":4,"win_probability":0.18}],"confidence":80}
```"""

    parsed = parse_prediction_output(output, 1.0)

    assert parsed is not None
    assert parsed["predicted"] == [1, 2, 5]
    assert parsed["top3"] == [1, 2, 5]
    assert parsed["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 5},
    ]
    assert parsed["prediction_validation"]["valid"] is True
    assert parsed["prediction_validation"]["normalized_candidate_count"] == 3
    assert [
        row["chulNo"]
        for row in parsed["prediction_validation"]["normalized_candidates"]
    ] == [
        1,
        2,
        5,
    ]


def test_parse_prediction_output_rejects_horse_outside_race_card() -> None:
    output = """```json
{"selected_horses":[{"chulNo":1},{"chulNo":2},{"chulNo":9}],"confidence":80}
```"""

    assert (
        parse_prediction_output(
            output,
            1.0,
            race_data={"horses": [{"chulNo": 1}, {"chulNo": 2}, {"chulNo": 3}]},
        )
        is None
    )


def test_finalize_prediction_payload_rejects_underfilled_contract_without_race_card() -> (
    None
):
    assert (
        finalize_prediction_payload(
            {"selected_horses": [{"chulNo": 1}, {"chulNo": 2}]},
            execution_time=0.2,
        )
        is None
    )


def test_finalize_prediction_payload_reuses_guarded_top3_for_downstream() -> None:
    finalized = finalize_prediction_payload(
        {
            "selected_horses": [
                {"chulNo": 1},
                {"chulNo": "bad"},
                {"chulNo": 2},
            ],
            "confidence": 80,
        },
        execution_time=0.2,
        race_data=_race_data_with_horses(1, 2, 3),
    )

    assert finalized is not None
    assert finalized["predicted"] == [1, 2, 3]
    assert finalized["top3"] == [1, 2, 3]
    assert finalized["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert finalized["prediction_output_format"] == {
        "version": "unordered-top3-unique-v1",
        "predicted_count": 3,
        "is_unique": True,
    }
