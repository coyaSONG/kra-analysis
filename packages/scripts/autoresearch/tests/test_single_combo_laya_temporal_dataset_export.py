"""Tests for the strict temporal Laya dataset exporter."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (
    single_combo_laya_temporal_dataset_export as export,  # noqa: E402
)


def _config() -> dict[str, Any]:
    return {
        "rolling_windows": [
            {
                "name": "fold_a",
                "train_end": "20250101",
                "eval_start": "20250102",
                "eval_end": "20250102",
            },
            {
                "name": "fold_b",
                "train_end": "20250102",
                "eval_start": "20250103",
                "eval_end": "20250103",
            },
            {
                "name": "fold_c",
                "train_end": "20250103",
                "eval_start": "20250104",
                "eval_end": "20250104",
            },
        ]
    }


def _candidate(
    combo: tuple[int, int, int], answer: tuple[int, int, int]
) -> dict[str, Any]:
    overlap = len(set(combo) & set(answer))
    return {
        "race_id": "unused",
        "combo": combo,
        "is_default": float(combo == (1, 2, 4)),
        "default_overlap": 2.0,
        "member_mean": 0.7,
        "member_min": 0.5,
        "member_mean_delta": 0.1,
        "member_rank_sum": 6.0,
        "top3_count": 3.0,
        "top5_count": 3.0,
        "support_count": 2.0,
        "source_score": 0.8,
        "ensemble_score": 0.7,
        "probability": 0.6,
        "probability_delta": 0.1,
        "model_rank": 1.0,
        "exact_label": float(combo == answer),
        "match_label": overlap / 3.0,
    }


def _fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    answers: dict[str, list[int]] = {}
    candidates_by_window: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for day, window in ((2, "fold_a"), (3, "fold_b"), (4, "fold_c")):
        race_id = f"202501{day:02d}_1_1"
        answer = (1, 2, 3)
        answers[race_id] = list(answer)
        for chul_no in range(1, 7):
            rows.append(
                {
                    "race_id": race_id,
                    "race_date": f"202501{day:02d}",
                    "chulNo": chul_no,
                    "target": int(chul_no <= 3),
                    "dist": 1200,
                    "field_size": 6,
                    "age": 3 + chul_no % 2,
                    "rating": 10 - chul_no,
                    "horse_place_rate": float("nan") if chul_no == 6 else 0.2,
                }
            )
        candidates_by_window[window] = {
            race_id: [
                _candidate((1, 2, 3), answer),
                _candidate((1, 2, 4), answer),
                _candidate((1, 3, 4), answer),
            ]
        }
    candidate_cache = {
        "format_version": export.SOURCE_FORMAT_VERSION,
        "selection_contract": export.SOURCE_SELECTION_CONTRACT,
        "timing_contract": export.SOURCE_TIMING_CONTRACT,
        "is_partial_window_cache": False,
        "candidate_rows_by_window": candidates_by_window,
    }
    row_cache = {"rows": rows, "answers": answers}
    return candidate_cache, row_cache


def test_builds_disjoint_temporal_splits_without_rendering_labels() -> None:
    candidate_cache, row_cache = _fixture()
    datasets, manifest = export.build_laya_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=_config(),
    )

    assert manifest["status"] == "passed"
    assert manifest["coverage"]["race_count"] == 3
    assert manifest["coverage"]["split_overlap_race_ids"] == []
    assert manifest["timing_audit"]["passed"] is True
    assert manifest["leakage_audit"]["passed"] is True
    assert {name: len(rows) for name, rows in datasets.items()} == {
        "train": 1,
        "validation": 1,
        "test": 1,
    }
    rendered_inputs = json.dumps(
        {
            name: [
                {"state": row["state"], "questions": row["questions"]} for row in rows
            ]
            for name, rows in datasets.items()
        },
        sort_keys=True,
    )
    assert "exact_label" not in rendered_inputs
    assert "match_label" not in rendered_inputs
    assert '"target"' not in rendered_inputs
    for rows in datasets.values():
        row = rows[0]
        criteria = row["questions"][export.QUESTION_ID]["criteria"]
        assert 2 <= len(criteria) <= 20
        assert row["expected"][export.QUESTION_ID] in criteria


def test_answer_changes_only_expected_not_model_inputs() -> None:
    candidate_cache, row_cache = _fixture()
    original, _manifest = export.build_laya_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=_config(),
    )
    changed_cache = copy.deepcopy(candidate_cache)
    changed_rows = copy.deepcopy(row_cache)
    for race_id in changed_rows["answers"]:
        changed_rows["answers"][race_id] = [4, 5, 6]
    for window_rows in changed_cache["candidate_rows_by_window"].values():
        for _race_id, candidates in window_rows.items():
            answer = (4, 5, 6)
            for candidate in candidates:
                combo = tuple(candidate["combo"])
                candidate["exact_label"] = float(combo == answer)
                candidate["match_label"] = len(set(combo) & set(answer)) / 3.0
    changed, _manifest = export.build_laya_dataset(
        candidate_cache=changed_cache,
        row_cache=changed_rows,
        config=_config(),
    )

    for split_name in original:
        assert original[split_name][0]["state"] == changed[split_name][0]["state"]
        assert (
            original[split_name][0]["questions"] == changed[split_name][0]["questions"]
        )
        assert original[split_name][0]["expected"] != changed[split_name][0]["expected"]


def test_caps_combo_options_and_keeps_all_races_with_none_target() -> None:
    candidate_cache, row_cache = _fixture()
    answer = (4, 5, 6)
    for window_rows in candidate_cache["candidate_rows_by_window"].values():
        race_id = next(iter(window_rows))
        combos = []
        for first in range(1, 6):
            for second in range(first + 1, 7):
                for third in range(second + 1, 8):
                    combo = (first, second, third)
                    if combo == answer:
                        continue
                    row = _candidate(combo, answer)
                    row["support_count"] = float(20 - len(combos))
                    combos.append(row)
                    if len(combos) == 22:
                        break
                if len(combos) == 22:
                    break
            if len(combos) == 22:
                break
        window_rows[race_id] = combos
        row_cache["answers"][race_id] = list(answer)

    datasets, manifest = export.build_laya_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=_config(),
    )

    assert manifest["status"] == "passed"
    assert manifest["coverage"]["race_count"] == 3
    for split_name, rows in datasets.items():
        criteria = rows[0]["questions"][export.QUESTION_ID]["criteria"]
        expected = rows[0]["expected"][export.QUESTION_ID]
        assert len(criteria) == 20
        assert criteria[expected] == export.NONE_OPTION
        assert tuple(criteria) == export.OPTION_LABELS
        assert manifest["split_summaries"][split_name]["none_target_count"] == 1


def test_rejects_cross_split_race_overlap() -> None:
    candidate_cache, row_cache = _fixture()
    fold_a_id = next(iter(candidate_cache["candidate_rows_by_window"]["fold_a"]))
    fold_a_rows = candidate_cache["candidate_rows_by_window"]["fold_a"][fold_a_id]
    candidate_cache["candidate_rows_by_window"]["fold_b"][fold_a_id] = fold_a_rows

    _datasets, manifest = export.build_laya_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=_config(),
    )

    assert manifest["status"] == "failed"
    assert manifest["coverage"]["split_overlap_race_ids"] == [fold_a_id]


def test_rejects_source_label_inconsistency() -> None:
    candidate_cache, row_cache = _fixture()
    first_window = candidate_cache["candidate_rows_by_window"]["fold_a"]
    first_candidates = next(iter(first_window.values()))
    first_candidates[0]["exact_label"] = 0.0

    _datasets, manifest = export.build_laya_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=_config(),
    )

    assert manifest["status"] == "failed"
    assert manifest["leakage_audit"]["source_label_consistency_violations"]


def test_rejects_partial_candidate_cache() -> None:
    candidate_cache, row_cache = _fixture()
    candidate_cache["is_partial_window_cache"] = True

    with pytest.raises(ValueError, match="every canonical window"):
        export.build_laya_dataset(
            candidate_cache=candidate_cache,
            row_cache=row_cache,
            config=_config(),
        )
