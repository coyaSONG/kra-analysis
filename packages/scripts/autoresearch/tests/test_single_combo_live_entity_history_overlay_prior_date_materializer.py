"""Live entity-history overlay prior-date materializer tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_live_entity_history_overlay_prior_date_materializer as materializer,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_source_target(path: Path) -> None:
    _write_json(
        path,
        {
            "best": {
                "candidate": "clean_current_best_entity_history_overlay/fallback_only",
                "selector_spec": "fallback_only",
                "summary": {
                    "overfit_safe_exact_rate": 0.538462,
                    "test_exact_3of3_rate": 0.55102,
                    "robust_history_pool_oracle_exact_rate": 0.538462,
                },
                "windows": [
                    {
                        "name": "test",
                        "diagnostics": {
                            "history_update": "none",
                            "selection_uses_labels": False,
                            "selector": "fallback_only",
                            "switch_rate": 0.0,
                        },
                    }
                ],
            },
            "selection_contract": "clean_current_best_entity_history_overlay",
            "source_artifact": "offline-cross-surface-union-race-context.json",
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


def _write_passed_source(
    path: Path, predictions: dict[str, dict[str, list[int]]]
) -> None:
    predicted_count = sum(len(window) for window in predictions.values())
    _write_json(
        path,
        {
            "coverage": {
                "coverage_rate": 1.0,
                "predicted_race_count": predicted_count,
            },
            "predictions_by_window": predictions,
            "selection_contract": "one_unordered_top3_combo_per_race",
            "status": "passed",
        },
    )


def test_build_artifact_blocks_when_cross_surface_source_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "entity-overlay-target.json"
    candidates = tmp_path / "candidates.json"
    _write_source_target(source_target)
    _write_candidates(candidates)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=tmp_path / "missing-cross-surface.json",
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_missing_live_source_artifact"
    assert result["live_source_context"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_cross_surface_union_race_context_prior_date_source_to_live_runner"
    )
    assert result["predictions_by_window"] == {}
    assert result["policy"]["fallback_only_ranker_may_pass_through_materialized_source"]
    assert not result["counts_as_70_percent_evidence"]


def test_build_artifact_follows_cross_surface_child_action(tmp_path: Path) -> None:
    source_target = tmp_path / "entity-overlay-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "cross-surface-source.json"
    _write_source_target(source_target)
    _write_candidates(candidates, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 0.0, "predicted_race_count": 0},
            "recommended_next_action": {
                "action": "port_locked_best_broad_component_first_exact_rank_prior_date_source_to_live_runner",
                "blocking": False,
                "queue_priority_score": 94.94,
                "reason": "broad-component first-exact rank source is missing",
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
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_broad_component_first_exact_rank_prior_date_source_to_live_runner"
    )
    assert result["recommended_next_action"]["upstream_action"] == (
        "port_locked_best_entity_history_overlay_prior_date_source_to_live_runner"
    )


def test_build_artifact_passes_through_fallback_only_source(tmp_path: Path) -> None:
    source_target = tmp_path / "entity-overlay-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "cross-surface-source.json"
    _write_source_target(source_target)
    race_ids = _write_candidates(candidates, race_count=2)
    predictions = {"live": {race_ids[0]: [1, 2, 3], race_ids[1]: [2, 4, 7]}}
    _write_passed_source(source, predictions)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
    )

    assert result["status"] == "passed"
    assert result["diagnostic_only"] is False
    assert result["coverage"]["coverage_rate"] == 1.0
    assert result["predictions_by_window"] == predictions
    assert result["recommended_next_action"]["action"] == (
        "materialize_locked_best_entity_history_pair_overlay_from_passed_entity_history_overlay"
    )
