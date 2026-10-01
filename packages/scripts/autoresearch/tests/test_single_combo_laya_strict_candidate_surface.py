"""Tests for the strict prior-date Laya candidate replay surface."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_laya_strict_candidate_surface as surface,
)


def _row_cache() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    answers: dict[str, list[int]] = {}
    for day in range(1, 7):
        date = f"202501{day:02d}"
        race_id = f"{date}_1_1"
        answers[race_id] = [1, 2, 3]
        for chul_no in range(1, 7):
            rows.append(
                {
                    "race_id": race_id,
                    "race_date": date,
                    "chulNo": chul_no,
                    "target": int(chul_no <= 3),
                    "rating": float(10 - chul_no),
                }
            )
    return {"dataset": "fixture", "rows": rows, "answers": answers}


def _provider(
    train_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    block: surface.ReplayBlock,
) -> dict[str, dict[str, dict[int, float]]]:
    assert train_rows
    assert all(str(row["race_date"]) <= block.train_end for row in train_rows)
    assert all(str(row["race_date"]) >= block.eval_start for row in eval_rows)
    assert all(str(row["race_date"]) <= block.eval_end for row in eval_rows)
    assert all(row["target"] == 0 for row in eval_rows)
    race_ids = sorted({str(row["race_id"]) for row in eval_rows})
    return {
        member_key: {
            race_id: {
                chul_no: (1.0 / chul_no) + member_offset for chul_no in range(1, 7)
            }
            for race_id in race_ids
        }
        for member_key, member_offset in (("m1", 0.0), ("m2", 0.01))
    }


def test_build_replay_blocks_never_splits_or_trains_on_active_date() -> None:
    rows = _row_cache()["rows"]
    assert isinstance(rows, list)

    blocks, warmup = surface.build_replay_blocks(
        rows,
        min_train_races=1,
        refit_date_stride=2,
    )

    assert len(warmup) == 1
    assert [block.eval_dates for block in blocks] == [
        ("20250102", "20250103"),
        ("20250104", "20250105"),
        ("20250106",),
    ]
    assert all(block.train_end < block.eval_start for block in blocks)
    assert [block.train_race_count for block in blocks] == [1, 3, 5]


def test_candidate_selection_is_unique_and_label_free() -> None:
    probabilities = _provider(
        [
            {
                "race_id": "20250101_1_1",
                "race_date": "20250101",
                "chulNo": 1,
                "target": 1,
            }
        ],
        [
            {
                "race_id": "20250102_1_1",
                "race_date": "20250102",
                "chulNo": chul_no,
                "target": 0,
            }
            for chul_no in range(1, 7)
        ],
        surface.ReplayBlock(
            "block_001",
            "20250101",
            "20250102",
            "20250102",
            ("20250102",),
            1,
            1,
        ),
    )
    all_candidates = surface.build_all_candidates(
        member_probabilities_by_key=probabilities,
        member_keys=("m1", "m2"),
        race_id="20250102_1_1",
        method="rank_mean",
        max_rank=6,
    )
    selected = surface.select_candidates(
        all_candidates=all_candidates,
        history={},
        candidate_count=19,
    )

    assert len(all_candidates) == 20
    assert len(selected) == 19
    assert len({tuple(row["combo"]) for row in selected}) == 19
    assert selected[0]["policy_name"] == "pattern1-2-3"
    assert all("exact_label" not in row for row in selected)
    assert all("match_label" not in row for row in selected)
    assert all("answer" not in row for row in selected)


def test_pattern_history_uses_completed_races_only() -> None:
    candidates = {
        "race": {
            "pattern1-2-3": {"combo": [1, 2, 4]},
            "pattern2-3-4": {"combo": [1, 2, 3]},
        }
    }
    history: dict[str, dict[str, float]] = {}

    before = surface.ordered_pattern_names(list(candidates["race"]), history)
    surface.update_pattern_history(
        history=history,
        all_candidates_by_race=candidates,
        answers={"race": (1, 2, 3)},
    )
    after = surface.ordered_pattern_names(list(candidates["race"]), history)

    assert before[0] == "pattern1-2-3"
    assert after[0] == "pattern2-3-4"
    assert history["pattern2-3-4"]["exact_count"] == 1.0


def test_build_surface_preserves_strict_block_contract() -> None:
    payload = surface.build_strict_candidate_surface(
        row_cache=_row_cache(),
        probability_provider=_provider,
        member_keys=("m1", "m2"),
        probability_method="rank_mean",
        base_specs=[
            {"model_name": "m1", "feature_set_name": "fixture"},
            {"model_name": "m2", "feature_set_name": "fixture"},
        ],
        min_train_races=1,
        refit_date_stride=2,
        candidate_count=19,
        max_rank=6,
    )

    assert payload["status"] == "passed"
    assert payload["replay_complete"] is True
    assert payload["counts_as_70_percent_evidence"] is False
    assert payload["coverage"]["source_race_count"] == 6
    assert payload["coverage"]["warmup_skipped_race_count"] == 1
    assert payload["coverage"]["eligible_race_count"] == 5
    assert payload["coverage"]["candidate_race_count"] == 5
    assert payload["candidate_oracle"]["exact_rate"] == 1.0
    assert payload["candidate_oracle"]["min_block_exact_rate"] == 1.0
    assert (
        payload["candidate_oracle"]["meets_70_percent_overall_and_block_floor"] is True
    )
    assert payload["recommended_next_action"] == "export_laya_temporal_jsonl"
    assert [row["pattern_history_race_count_before"] for row in payload["blocks"]] == [
        0,
        2,
        4,
    ]
    for race in payload["candidates_by_race"].values():
        assert race["timing"]["fit_through_date"] < race["race_date"]
        assert race["timing"]["selection_uses_active_block_labels"] is False
        assert len(race["candidates"]) == 19
        assert all("exact_label" not in row for row in race["candidates"])
