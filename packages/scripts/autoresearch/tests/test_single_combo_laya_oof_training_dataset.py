"""Tests for the expanded OOF Laya training dataset."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_laya_oof_training_dataset as dataset,
)


def _candidate(
    race_id: str,
    combo: tuple[int, int, int],
    answer: tuple[int, int, int],
) -> dict[str, Any]:
    return {
        "race_id": race_id,
        "combo": combo,
        "is_default": float(combo == (1, 2, 4)),
        "default_overlap": 2.0,
        "member_mean": 0.7,
        "support_count": 2.0,
        "source_score": 0.8,
        "ensemble_score": 0.7,
        "probability": 0.6,
        "model_rank": 1.0,
        "exact_label": float(combo == answer),
        "match_label": len(set(combo) & set(answer)) / 3.0,
    }


def _fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    train_ids = ("20250101_1_1", "20250102_1_1")
    validation_ids = ("20250103_1_1",)
    answer = (1, 2, 3)
    candidate_rows_by_split: dict[str, dict[str, list[dict[str, Any]]]] = {
        "train": {},
        "validation": {},
    }
    answers_by_split: dict[str, dict[str, list[int]]] = {
        "train": {},
        "validation": {},
    }
    rows: list[dict[str, Any]] = []
    master_answers: dict[str, list[int]] = {}
    for split_name, race_ids in (
        ("train", train_ids),
        ("validation", validation_ids),
    ):
        for race_id in race_ids:
            candidate_rows_by_split[split_name][race_id] = [
                _candidate(race_id, (1, 2, 3), answer),
                _candidate(race_id, (1, 2, 4), answer),
                _candidate(race_id, (1, 3, 4), answer),
            ]
            answers_by_split[split_name][race_id] = list(answer)
            master_answers[race_id] = list(answer)
            for chul_no in range(1, 7):
                rows.append(
                    {
                        "race_id": race_id,
                        "race_date": race_id[:8],
                        "chulNo": chul_no,
                        "target": int(chul_no <= 3),
                        "dist": 1200,
                        "age": 3,
                        "rating": 10 - chul_no,
                    }
                )
    candidate_cache = {
        "format_version": dataset.CANDIDATE_CACHE_FORMAT_VERSION,
        "train_prediction_contract": dataset.TRAIN_PREDICTION_CONTRACT,
        "train_window": "fold_a",
        "validation_window": "fold_a",
        "is_partial_date_group_surface": False,
        "candidate_rows_by_split": candidate_rows_by_split,
        "answers_by_split": answers_by_split,
        "source_contracts": {
            "label_usage": "labels_attached_after_candidate_generation"
        },
    }
    row_cache = {"rows": rows, "answers": master_answers}
    config = {
        "rolling_windows": [
            {
                "name": "fold_a",
                "train_end": "20250102",
                "eval_start": "20250103",
                "eval_end": "20250103",
            }
        ]
    }
    return candidate_cache, row_cache, config


def test_builds_disjoint_train_and_validation_without_test_or_labels() -> None:
    candidate_cache, row_cache, config = _fixture()

    datasets, manifest = dataset.build_laya_oof_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=config,
    )

    assert manifest["status"] == "passed"
    assert set(datasets) == {"train", "validation"}
    assert {name: len(rows) for name, rows in datasets.items()} == {
        "train": 2,
        "validation": 1,
    }
    assert manifest["coverage"]["split_overlap_race_ids"] == []
    assert manifest["timing_audit"]["chronological_split_order"] is True
    assert manifest["holdout_policy"] == "no_test_split_exported_december_2025_is_spent"
    rendered = json.dumps(datasets, sort_keys=True)
    assert "exact_label" not in rendered
    assert "match_label" not in rendered
    assert '"target"' not in rendered


def test_answer_change_does_not_change_model_inputs() -> None:
    candidate_cache, row_cache, config = _fixture()
    original, _manifest = dataset.build_laya_oof_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=config,
    )
    changed_cache = copy.deepcopy(candidate_cache)
    changed_rows = copy.deepcopy(row_cache)
    new_answer = (4, 5, 6)
    for split_name, answers in changed_cache["answers_by_split"].items():
        for race_id in answers:
            answers[race_id] = list(new_answer)
            changed_rows["answers"][race_id] = list(new_answer)
            for candidate in changed_cache["candidate_rows_by_split"][split_name][
                race_id
            ]:
                combo = tuple(candidate["combo"])
                candidate["exact_label"] = float(combo == new_answer)
                candidate["match_label"] = len(set(combo) & set(new_answer)) / 3.0
    changed, _manifest = dataset.build_laya_oof_dataset(
        candidate_cache=changed_cache,
        row_cache=changed_rows,
        config=config,
    )

    for split_name in original:
        for before, after in zip(original[split_name], changed[split_name], strict=True):
            assert before["state"] == after["state"]
            assert before["questions"] == after["questions"]
            assert before["expected"] != after["expected"]


def test_rejects_partial_or_unsafe_candidate_cache() -> None:
    candidate_cache, row_cache, config = _fixture()
    candidate_cache["is_partial_date_group_surface"] = True
    with pytest.raises(ValueError, match="every target train date group"):
        dataset.build_laya_oof_dataset(
            candidate_cache=candidate_cache,
            row_cache=row_cache,
            config=config,
        )

    candidate_cache["is_partial_date_group_surface"] = False
    candidate_cache["train_prediction_contract"] = "unsafe"
    with pytest.raises(ValueError, match="date-ordered OOF contract"):
        dataset.build_laya_oof_dataset(
            candidate_cache=candidate_cache,
            row_cache=row_cache,
            config=config,
        )


def test_marks_temporal_overlap_as_failed() -> None:
    candidate_cache, row_cache, config = _fixture()
    race_id = "20250103_1_1"
    candidate_cache["candidate_rows_by_split"]["train"][race_id] = copy.deepcopy(
        candidate_cache["candidate_rows_by_split"]["validation"][race_id]
    )
    candidate_cache["answers_by_split"]["train"][race_id] = [1, 2, 3]

    _datasets, manifest = dataset.build_laya_oof_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=config,
    )

    assert manifest["status"] == "failed"
    assert manifest["coverage"]["split_overlap_race_ids"] == [race_id]
    assert "train:20250103_1_1" in manifest["timing_audit"]["violations"]


def test_rejects_candidate_answer_race_id_mismatch() -> None:
    candidate_cache, row_cache, config = _fixture()
    candidate_cache["answers_by_split"]["train"].pop("20250101_1_1")

    with pytest.raises(ValueError, match="candidate and answer race IDs differ"):
        dataset.build_laya_oof_dataset(
            candidate_cache=candidate_cache,
            row_cache=row_cache,
            config=config,
        )
