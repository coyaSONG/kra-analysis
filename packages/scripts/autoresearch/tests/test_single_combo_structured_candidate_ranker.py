"""Tests for the structured top-three candidate ranker."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_structured_candidate_ranker as ranker,
)


def _row(
    race_id: str = "20250701_1_1", *, expected_label: str = "B"
) -> dict[str, Any]:
    fields = ["number", *ranker.RUNNER_FIELDS]
    runners = [
        [number, 3, 0, 40 + number, 550, number, 200, 300, 400, 500, 30]
        for number in range(1, 6)
    ]
    return {
        "state": {
            "race_id": race_id,
            "meet": 1,
            "race_no": 1,
            "distance": 1200,
            "field_size": 5,
            "class": 4,
            "weather": 1,
            "track_pct": 3,
            "wet": 0,
            "handicap": 1,
            "runner_fields": fields,
            "runner_values": runners,
        },
        "questions": {
            ranker.QUESTION_ID: {
                "type": "choice",
                "instructions": "Choose.",
                "criteria": {
                    "A": "1,2,3|1,3,800,700,1,650,600",
                    "B": "2,3,4|0,2,500,400,2,550,500",
                    "C": ranker.NONE_OPTION,
                },
            }
        },
        "expected": {ranker.QUESTION_ID: expected_label},
    }


def test_structured_features_match_contract_and_candidate_values() -> None:
    row = _row()
    features = ranker.structured_candidate_features(
        "1,2,3|1,3,800,700,1,650,600",
        state=row["state"],
        option_count=2,
    )

    assert len(features) == len(ranker.STRUCTURED_FEATURE_NAMES)
    assert features[ranker.STRUCTURED_FEATURE_NAMES.index("horse_number_mean")] == 2.0
    assert features[ranker.STRUCTURED_FEATURE_NAMES.index("rating_mean")] == 42.0
    assert np.isfinite(np.asarray(features, dtype=np.float64)).all()


def test_build_examples_excludes_none_and_marks_pool_miss() -> None:
    candidate_hit, pool_miss = ranker.build_examples(
        [_row(), _row("20250702_1_1", expected_label="C")]
    )

    assert len(candidate_hit["features"]) == 2
    assert candidate_hit["expected_index"] == 1
    assert pool_miss["expected_index"] is None


def test_temporal_split_keeps_dates_disjoint() -> None:
    examples = ranker.build_examples(
        [
            _row("20250701_1_1"),
            _row("20250702_1_1"),
            _row("20250703_1_1"),
            _row("20250704_1_1"),
            _row("20250705_1_1"),
        ]
    )

    train, validation, cutoff = ranker.temporal_inner_split(examples, 0.4)

    assert cutoff == "20250704"
    assert {example["race_date"] for example in train} == {
        "20250701",
        "20250702",
        "20250703",
    }
    assert {example["race_date"] for example in validation} == {
        "20250704",
        "20250705",
    }


def test_scoring_counts_pool_miss_as_top3_failure() -> None:
    examples = ranker.build_examples(
        [_row(), _row("20250702_1_1", expected_label="C")]
    )
    metrics, predictions = ranker.score_predictions(
        examples,
        np.asarray([0.1, 0.9, 0.9, 0.1], dtype=np.float32),
    )

    assert metrics["top3_correct_count"] == 1
    assert metrics["top3_exact_accuracy"] == 0.5
    assert metrics["candidate_oracle_exact_accuracy"] == 0.5
    assert [prediction["top3_correct"] for prediction in predictions] == [True, False]
