"""Live row-cache rank-pattern prior-date materializer tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_live_row_cache_rank_pattern_prior_date_materializer as materializer,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_source_target(path: Path) -> None:
    _write_json(
        path,
        {
            "best": {
                "candidate": (
                    "clean_current_best_row_cache_rank_pattern/top20/hgb/exact/"
                    "score0.3/srcex0.08/ov2/srcw0/rankw0/ovw0.05/srcrankpen0.01"
                ),
                "selector_spec": (
                    "score0.3/srcex0.08/ov2/srcw0/rankw0/ovw0.05/srcrankpen0.01"
                ),
                "summary": {
                    "overfit_safe_exact_rate": 0.538462,
                    "test_exact_3of3_rate": 0.557823,
                    "robust_pool_oracle_exact_rate": 0.775862,
                },
                "windows": [
                    {
                        "name": "test",
                        "diagnostics": {
                            "model_fit": True,
                            "selection_uses_labels": False,
                            "switch_rate": 0.027211,
                        },
                    }
                ],
            },
            "selection_contract": "one_unordered_top3_combo_per_race",
            "source_artifact": "offline-entity-history-pair-overlay.json",
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


def _write_passed_source(path: Path, race_ids: list[str]) -> None:
    _write_json(
        path,
        {
            "coverage": {
                "coverage_rate": 1.0,
                "predicted_race_count": len(race_ids),
            },
            "predictions_by_window": {
                "live": {race_id: [1, 2, 3] for race_id in race_ids}
            },
            "selection_contract": "one_unordered_top3_combo_per_race",
            "status": "passed",
        },
    )


def test_build_artifact_blocks_when_pair_overlay_source_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "row-cache-target.json"
    candidates = tmp_path / "candidates.json"
    _write_source_target(source_target)
    _write_candidates(candidates)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=tmp_path / "missing-pair-overlay.json",
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_missing_live_source_artifact"
    assert result["live_source_context"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_entity_history_pair_overlay_prior_date_source_to_live_runner"
    )
    assert result["coverage"]["predicted_race_count"] == 0
    assert result["predictions_by_window"] == {}
    assert result["policy"]["ranker_must_not_be_treated_as_pass_through"]
    assert not result["counts_as_70_percent_evidence"]


def test_build_artifact_follows_pair_overlay_child_action(tmp_path: Path) -> None:
    source_target = tmp_path / "row-cache-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "pair-overlay-source.json"
    _write_source_target(source_target)
    _write_candidates(candidates, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 0.0, "predicted_race_count": 0},
            "recommended_next_action": {
                "action": "port_locked_best_entity_history_overlay_prior_date_source_to_live_runner",
                "blocking": False,
                "queue_priority_score": 94.9,
                "reason": "entity-history overlay source is missing",
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
        "port_locked_best_entity_history_overlay_prior_date_source_to_live_runner"
    )
    assert result["recommended_next_action"]["upstream_action"] == (
        "port_locked_best_row_cache_rank_pattern_prior_date_source_to_live_runner"
    )


def test_build_artifact_blocks_pending_model_logic_after_source_materialization(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "row-cache-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "pair-overlay-source.json"
    _write_source_target(source_target)
    race_ids = _write_candidates(candidates, race_count=2)
    _write_passed_source(source, race_ids)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
    )

    assert (
        result["status"]
        == "blocked_pending_row_cache_rank_pattern_prior_date_prediction_logic"
    )
    assert result["diagnostic_only"] is True
    assert result["predictions_by_window"] == {}
    assert result["selector_diagnostics"][
        "prediction_logic_pending_after_source_materialization"
    ]
    assert result["recommended_next_action"]["action"] == (
        "implement_locked_best_row_cache_rank_pattern_prior_date_prediction_logic"
    )
    assert result["policy"]["hgb_model_prediction_logic_must_be_ported_before_emit"]
