"""Live row-cache rank-pattern after-broad-rank-segment materializer tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_live_row_cache_rank_pattern_after_broad_rank_segment_materializer as materializer,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_source_target(path: Path) -> None:
    _write_json(
        path,
        {
            "best": {
                "selector_spec": "fallback_only",
            },
            "selection_contract": "one_unordered_top3_combo_per_race",
            "source_artifact": "offline-broad-component-rank-segment-source.json",
        },
    )


def _write_candidates(path: Path, *, race_count: int = 2) -> list[str]:
    race_ids = [f"r{index}" for index in range(1, race_count + 1)]
    _write_json(
        path,
        {
            "coverage": {
                "candidate_race_count": race_count,
                "expected_race_count": race_count,
                "missing_race_ids": [],
                "race_ids": race_ids,
            },
            "current_candidates_by_race": {
                race_id: {"combo": [1, 2, 3]} for race_id in race_ids
            },
            "live_records": [{"race_id": race_id} for race_id in race_ids],
            "status": "passed",
        },
    )
    return race_ids


def test_build_artifact_blocks_when_broad_component_rank_segment_source_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "row-cache-target.json"
    candidates = tmp_path / "candidates.json"
    missing_source = tmp_path / "missing-broad-component-rank-segment-source.json"
    _write_source_target(source_target)
    _write_candidates(candidates)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=missing_source,
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_missing_live_source_artifact"
    assert result["live_source_context"]["status"] == "missing"
    assert result["candidate_feature_context"]["status"] == "passed"
    assert result["predictions_by_window"] == {}
    assert result["selection_contract"] == "one_unordered_top3_combo_per_race"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_broad_component_rank_segment_after_row_cache_rank_pattern_source_to_live_runner"
    )
    assert result["policy"][
        "prior_date_history_must_not_include_current_or_future_labels"
    ]
    assert not result["counts_as_70_percent_evidence"]


def test_build_artifact_follows_broad_component_rank_segment_child_action(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "row-cache-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "broad-component-rank-segment-source.json"
    _write_source_target(source_target)
    _write_candidates(candidates, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 0.0, "predicted_race_count": 0},
            "recommended_next_action": {
                "action": "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner",
                "blocking": False,
                "queue_priority_score": 94.74,
                "reason": "row-cache rank-pattern after source-pool source is missing",
            },
            "status": "blocked_missing_live_source_artifact",
        },
    )

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_live_source_child_dependency"
    assert result["live_source_context"]["status"] == "failed"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner"
    )
    assert result["recommended_next_action"]["upstream_action"] == (
        "port_locked_best_broad_component_rank_segment_after_row_cache_rank_pattern_source_to_live_runner"
    )


def test_build_artifact_passes_through_fallback_only_source(tmp_path: Path) -> None:
    source_target = tmp_path / "row-cache-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "broad-component-rank-segment-source.json"
    _write_source_target(source_target)
    race_ids = _write_candidates(candidates, race_count=2)
    _write_json(
        source,
        {
            "coverage": {
                "coverage_rate": 1.0,
                "expected_race_count": 2,
                "predicted_race_count": 2,
            },
            "predictions_by_window": {
                "live": {
                    race_ids[0]: [1, 2, 3],
                    race_ids[1]: [2, 3, 4],
                }
            },
            "selection_contract": (
                "live_current_best_plus_broad_component_rank_segment_prior_date_selector_predictions_by_window"
            ),
            "source_selection_contract": (
                "clean_current_best_plus_broad_component_rank_segment_prior_date_selector"
            ),
            "status": "passed",
        },
    )

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
    )

    assert result["status"] == "passed"
    assert result["diagnostic_only"] is False
    assert result["coverage"]["coverage_rate"] == 1.0
    assert result["live_source_context"]["contract_match"] is True
    assert result["predictions_by_window"] == {
        "live": {
            race_ids[0]: [1, 2, 3],
            race_ids[1]: [2, 3, 4],
        }
    }
    assert result["recommended_next_action"]["action"] == (
        "materialize_locked_best_full_combo_delta_switch_after_broad_rank_segment_from_passed_row_cache"
    )
    assert result["policy"]["fallback_only_broad_rank_segment_pass_through"]
