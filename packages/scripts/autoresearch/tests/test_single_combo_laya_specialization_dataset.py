"""Tests for Laya specialization option-order augmentation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_laya_specialization_dataset as specialization,
)


def _source_row(race_id: str = "20251002_1_1") -> dict[str, Any]:
    criteria = {
        "C01": "horses=1,2,4; score=0.8",
        "C02": "No listed combination is correct; use the fallback policy.",
        "C03": "horses=1,2,3; score=0.9",
        "C04": "horses=2,3,4; score=0.7",
    }
    return {
        "state": {"race_id": race_id, "runner_fields": ["number"]},
        "questions": {
            specialization.QUESTION_ID: {
                "type": "choice",
                "instructions": "Select one.",
                "criteria": criteria,
            }
        },
        "expected": {specialization.QUESTION_ID: "C03"},
        "tags": ["split:train"],
        "language": "en",
    }


def test_builds_deterministic_distinct_option_order_augmentations() -> None:
    rows, manifest = specialization.build_specialization_dataset(
        [_source_row()],
        augmentations_per_race=4,
        label_smoothing=0.05,
        seed="fixture",
    )
    repeated, repeated_manifest = specialization.build_specialization_dataset(
        [_source_row()],
        augmentations_per_race=4,
        label_smoothing=0.05,
        seed="fixture",
    )

    assert rows == repeated
    assert manifest == repeated_manifest
    assert manifest["status"] == "passed"
    assert manifest["independent_race_count"] == 1
    assert manifest["training_row_count"] == 4
    assert manifest["distinct_permutations_per_race_min"] == 4
    assert len({json.dumps(row["questions"], sort_keys=False) for row in rows}) == 4


def test_gold_distribution_tracks_relabelled_expected_description() -> None:
    source = _source_row()
    expected_description = source["questions"][specialization.QUESTION_ID]["criteria"][
        "C03"
    ]
    rows, _manifest = specialization.build_specialization_dataset(
        [source],
        augmentations_per_race=3,
        label_smoothing=0.1,
    )

    for row in rows:
        question = row["questions"][specialization.QUESTION_ID]
        expected = row["expected"][specialization.QUESTION_ID]
        probabilities = row["gold"][specialization.QUESTION_ID]["probabilities"]
        assert tuple(question["criteria"]) == specialization.OPTION_LABELS[:4]
        assert question["criteria"][expected] == expected_description
        assert probabilities[expected] == pytest.approx(0.9)
        assert sum(probabilities.values()) == pytest.approx(1.0)
        assert set(probabilities) == set(question["criteria"])


def test_augmentation_never_changes_state_or_option_meaning() -> None:
    source = _source_row()
    source_descriptions = set(
        source["questions"][specialization.QUESTION_ID]["criteria"].values()
    )
    rows, _manifest = specialization.build_specialization_dataset(
        [source],
        augmentations_per_race=5,
    )

    for row in rows:
        assert row["state"] == source["state"]
        assert (
            set(row["questions"][specialization.QUESTION_ID]["criteria"].values())
            == source_descriptions
        )
        assert "exact_label" not in json.dumps(row["questions"])
        assert "match_label" not in json.dumps(row["questions"])


def test_rejects_duplicate_independent_races() -> None:
    with pytest.raises(ValueError, match="one example per independent race"):
        specialization.build_specialization_dataset(
            [_source_row(), _source_row()],
        )


def test_rejects_invalid_smoothing() -> None:
    with pytest.raises(ValueError, match="label smoothing"):
        specialization.build_specialization_dataset(
            [_source_row()],
            label_smoothing=1.0,
        )
