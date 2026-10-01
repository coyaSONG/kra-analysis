"""Tests for position-balanced Laya option rotation evaluation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_laya_order_rotation_evaluation as rotation,
)


def _row() -> dict[str, Any]:
    return {
        "state": {"race_id": "20251001_1_1"},
        "questions": {
            "top3_combo": {
                "type": "choice",
                "instructions": "Choose.",
                "criteria": {"A": "a", "B": "b", "C": "c"},
            }
        },
        "expected": {"top3_combo": "B"},
    }


def test_build_rotation_rows_places_every_option_in_every_slot() -> None:
    rows = rotation.build_rotation_rows([_row()])

    assert [
        list(row["questions"]["top3_combo"]["criteria"]) for row in rows
    ] == [["A", "B", "C"], ["B", "C", "A"], ["C", "A", "B"]]
    assert [row["metadata"]["augmentation_index"] for row in rows] == [0, 1, 2]


def test_rotation_ensemble_aligns_labels_before_averaging() -> None:
    records = [
        {
            "race_id": "20251001_1_1",
            "augmentation_index": 0,
            "logits": [3.0, 2.0, 0.0],
            "expected_label": "B",
            "expected_description": "b",
            "labels": ["A", "B", "C"],
            "descriptions": ["a", "b", "c"],
        },
        {
            "race_id": "20251001_1_1",
            "augmentation_index": 1,
            "logits": [3.0, 0.0, 1.0],
            "expected_label": "B",
            "expected_description": "b",
            "labels": ["B", "C", "A"],
            "descriptions": ["b", "c", "a"],
        },
        {
            "race_id": "20251001_1_1",
            "augmentation_index": 2,
            "logits": [0.0, 1.0, 3.0],
            "expected_label": "B",
            "expected_description": "b",
            "labels": ["C", "A", "B"],
            "descriptions": ["c", "a", "b"],
        },
    ]

    metrics, predictions = rotation.aggregate_rotation_records(records)

    assert metrics["top3_exact_accuracy"] == 1.0
    assert metrics["stable_race_rate"] == 0.0
    assert predictions[0]["predicted_label"] == "B"
    assert predictions[0]["unique_variant_prediction_count"] == 2
