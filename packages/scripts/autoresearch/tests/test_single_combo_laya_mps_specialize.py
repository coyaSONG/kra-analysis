"""Unit tests for the Laya head-only specialization runner."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import single_combo_laya_mps_specialize as specialize  # noqa: E402


def _row(race_id: str, augmentation_index: int) -> dict[str, Any]:
    return {
        "state": {"race_id": race_id},
        "questions": {
            specialize.QUESTION_ID: {
                "type": "choice",
                "instructions": "Choose.",
                "criteria": {"A": "1,2,3", "B": specialize.NONE_OPTION},
            }
        },
        "expected": {specialize.QUESTION_ID: "A"},
        "metadata": {"augmentation_index": augmentation_index},
    }


def test_epoch_schedule_uses_one_variant_per_independent_race() -> None:
    rows = [
        _row(race_id, augmentation)
        for race_id in ("20251001_1_1", "20251001_1_2")
        for augmentation in range(3)
    ]

    schedule = specialize.validate_training_schedule(rows)
    second_epoch = specialize.epoch_rows(
        rows,
        epoch=2,
        augmentations_per_race=schedule["augmentations_per_race"],
    )

    assert schedule == {
        "independent_race_count": 2,
        "augmentations_per_race": 3,
        "training_row_count": 6,
    }
    assert len(second_epoch) == 2
    assert {row["metadata"]["augmentation_index"] for row in second_epoch} == {1}
    assert len({row["state"]["race_id"] for row in second_epoch}) == 2


def test_schedule_rejects_missing_or_duplicate_augmentations() -> None:
    with pytest.raises(ValueError, match="duplicate augmentation"):
        specialize.validate_training_schedule(
            [_row("20251001_1_1", 0), _row("20251001_1_1", 0)]
        )
    with pytest.raises(ValueError, match="same augmentation count"):
        specialize.validate_training_schedule(
            [
                _row("20251001_1_1", 0),
                _row("20251001_1_1", 1),
                _row("20251001_1_2", 0),
            ]
        )


def test_score_records_reports_exact_and_none_strata() -> None:
    records = [
        {
            "logits": [3.0, 1.0],
            "expected_index": 0,
            "expected_description": "1,2,3",
        },
        {
            "logits": [1.0, 2.0],
            "expected_index": 1,
            "expected_description": specialize.NONE_OPTION,
        },
    ]

    metrics = specialize.score_records(records)

    assert metrics["race_count"] == 2
    assert metrics["exact_accuracy"] == 1.0
    assert metrics["top3_exact_accuracy"] == 0.5
    assert metrics["top3_correct_count"] == 1
    assert metrics["candidate_target_accuracy"] == 1.0
    assert metrics["none_target_accuracy"] == 1.0
    assert metrics["predicted_position_distribution"] == {"1": 1, "2": 1}


def test_temperature_fit_is_bounded_and_reduces_nll() -> None:
    records = [
        {
            "logits": [4.0, 0.0],
            "expected_index": index % 2,
            "expected_description": "candidate",
        }
        for index in range(20)
    ]

    temperature = specialize.fit_temperature(records)

    assert 0.5 <= temperature <= 5.0
    assert (
        specialize.score_records(records, temperature)["nll"]
        < specialize.score_records(records, 1.0)["nll"]
    )


def test_model_selection_prefers_accuracy_then_nll() -> None:
    incumbent = {"top3_exact_accuracy": 0.5, "exact_accuracy": 0.5, "nll": 1.0}
    assert specialize._is_better(  # noqa: SLF001
        {"top3_exact_accuracy": 0.6, "exact_accuracy": 0.5, "nll": 2.0},
        incumbent,
    )
    assert specialize._is_better(  # noqa: SLF001
        {"top3_exact_accuracy": 0.5, "exact_accuracy": 0.6, "nll": 2.0},
        incumbent,
    )
    assert specialize._is_better(  # noqa: SLF001
        {"top3_exact_accuracy": 0.5, "exact_accuracy": 0.5, "nll": 0.9},
        incumbent,
    )
    assert not specialize._is_better(  # noqa: SLF001
        {"top3_exact_accuracy": 0.5, "exact_accuracy": 0.5, "nll": 1.1},
        incumbent,
    )
