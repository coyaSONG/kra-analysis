"""Tests for the frozen Laya candidate feature ranker."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import single_combo_laya_feature_ranker as ranker  # noqa: E402


def _row(race_id: str = "20251001_1_1") -> dict[str, Any]:
    return {
        "state": {"race_id": race_id, "field_size": 8},
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
        "expected": {ranker.QUESTION_ID: "B"},
    }


def test_parses_scaled_candidate_and_none_features() -> None:
    candidate = ranker.parse_candidate_description(
        "1,2,3|1,3,800,700,2,650,600",
        option_count=20,
        field_size=12,
    )
    none = ranker.parse_candidate_description(
        ranker.NONE_OPTION,
        option_count=20,
        field_size=12,
    )

    assert candidate == [0.0, 1.0, 3.0, 0.8, 0.7, 2.0, 0.65, 0.6, 20.0, 12.0]
    assert none == [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 20.0, 12.0]


def test_build_examples_preserves_race_groups_and_expected_index() -> None:
    examples = ranker.build_examples([_row(), _row("20251001_1_2")])
    features, labels, qid = ranker._flatten(examples)  # noqa: SLF001

    assert len(examples) == 2
    assert examples[0]["expected_index"] == 1
    assert features.shape == (6, len(ranker.FEATURE_NAMES))
    assert labels.tolist() == [0.0, 1.0, 0.0, 0.0, 1.0, 0.0]
    assert qid.tolist() == [0, 0, 0, 1, 1, 1]


def test_scores_one_prediction_per_race_and_none_strata() -> None:
    candidate_row = _row()
    none_row = _row("20251001_1_2")
    none_row["expected"][ranker.QUESTION_ID] = "C"
    examples = ranker.build_examples([candidate_row, none_row])
    metrics, predictions = ranker.score_predictions(
        examples,
        np.asarray([0.1, 0.8, 0.0, 0.1, 0.2, 0.9]),
    )

    assert metrics["exact_accuracy"] == 1.0
    assert metrics["top3_exact_accuracy"] == 0.5
    assert metrics["top3_correct_count"] == 1
    assert metrics["candidate_target_accuracy"] == 1.0
    assert metrics["none_target_accuracy"] == 1.0
    assert metrics["predicted_none_count"] == 1
    assert [prediction["top3_correct"] for prediction in predictions] == [True, False]
    assert len(predictions) == 2


def test_rejects_invalid_candidate_vector_and_duplicate_race() -> None:
    with pytest.raises(ValueError, match="seven values"):
        ranker.parse_candidate_description(
            "1,2,3|1,2",
            option_count=3,
            field_size=8,
        )
    with pytest.raises(ValueError, match="duplicate race_id"):
        ranker.build_examples([_row(), _row()])


def test_strict_baseline_comparison_requires_identical_race_universe() -> None:
    artifact = {
        "format_version": "fixture-v1",
        "best": {
            "candidate": "fixture/fallback",
            "windows": [
                {
                    "name": "fold_c",
                    "summary": {
                        "races": 2,
                        "exact_3of3": 1,
                        "exact_3of3_rate": 0.5,
                    },
                }
            ],
        },
        "predictions_by_window": {
            "fold_c": {"20251201_1_1": [1, 2, 3], "20251201_1_2": [1, 2, 4]}
        },
    }

    comparison = ranker.strict_baseline_comparison(
        artifact,
        race_ids={"20251201_1_1", "20251201_1_2"},
    )

    assert comparison["correct_count"] == 1
    assert comparison["exact_accuracy"] == 0.5
    with pytest.raises(ValueError, match="race universe"):
        ranker.strict_baseline_comparison(
            artifact,
            race_ids={"20251201_1_1"},
        )
