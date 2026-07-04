"""Live frontier artifact-combo prior-date materializer tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_live_frontier_artifact_combo_prior_date_materializer as materializer,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_source_target(
    path: Path,
    *,
    selected_current_best_rate: float = 1.0,
) -> None:
    _write_json(
        path,
        {
            "best": {
                "candidate": (
                    "clean_frontier_artifact_combo_prior_date/"
                    "exact1/hit20/match0/support0/recent0/cur0.05/minsrc1/prior5"
                ),
                "selector_spec": (
                    "exact1/hit20/match0/support0/recent0/cur0.05/minsrc1/prior5"
                ),
                "summary": {
                    "overfit_safe_exact_rate": 0.538462,
                    "test_exact_3of3_rate": 0.544218,
                    "robust_source_pool_oracle_exact_rate": 0.538462,
                },
                "windows": [
                    {
                        "name": "test",
                        "diagnostics": {
                            "feature_contract": (
                                "frontier_clean_artifact_output_prior_date_source_stats"
                            ),
                            "history_update": "completed_prior_eval_dates_only",
                            "selected_current_best_rate": selected_current_best_rate,
                            "selection_uses_labels": False,
                        },
                    }
                ],
            },
            "selection_contract": "clean_frontier_artifact_combo_prior_date_selector",
            "source_artifacts": ["offline-current-best-source.json"],
            "source_names": ["current_best_top15"],
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
            "selection_contract": "live_current_best_fallback_predictions_by_window",
            "status": "passed",
        },
    )


def test_build_artifact_blocks_when_live_current_best_source_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "frontier-target.json"
    candidates = tmp_path / "candidates.json"
    _write_source_target(source_target)
    _write_candidates(candidates)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=tmp_path / "missing-current-best.json",
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_missing_live_source_artifact"
    assert result["live_source_context"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "materialize_live_current_best_fallback_for_frontier_artifact_combo"
    )
    assert result["predictions_by_window"] == {}
    assert not result["counts_as_70_percent_evidence"]


def test_build_artifact_follows_live_current_best_child_action(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "frontier-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "current-best-source.json"
    _write_source_target(source_target)
    _write_candidates(candidates, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 0.0, "predicted_race_count": 0},
            "recommended_next_action": {
                "action": "repair_live_current_best_fallback_prediction_coverage",
                "blocking": False,
                "queue_priority_score": 95.0,
                "reason": "current-best fallback coverage is incomplete",
            },
            "selection_contract": "live_current_best_fallback_predictions_by_window",
            "status": "failed",
        },
    )

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_live_source_child_dependency"
    assert result["recommended_next_action"]["action"] == (
        "repair_live_current_best_fallback_prediction_coverage"
    )
    assert result["recommended_next_action"]["upstream_action"] == (
        "port_locked_best_frontier_artifact_combo_prior_date_source_to_live_runner"
    )


def test_build_artifact_passes_through_current_source_only_best(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "frontier-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "current-best-source.json"
    _write_source_target(source_target, selected_current_best_rate=1.0)
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
    assert result["selection_contract"] == "one_unordered_top3_combo_per_race"
    assert result["source_selection_contract"] == "one_unordered_top3_combo_per_race"
    assert (
        result["source_target_selection_contract"]
        == "clean_frontier_artifact_combo_prior_date_selector"
    )
    assert result["coverage"]["coverage_rate"] == 1.0
    assert result["predictions_by_window"] == predictions
    assert result["selector_diagnostics"]["best_selected_current_source_in_all_windows"]
    assert result["recommended_next_action"]["action"] == (
        "materialize_locked_best_broad_component_first_exact_rank_from_passed_frontier_artifact_combo"
    )


def test_build_artifact_blocks_when_best_is_not_current_source_only(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "frontier-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "current-best-source.json"
    _write_source_target(source_target, selected_current_best_rate=0.5)
    race_ids = _write_candidates(candidates, race_count=2)
    predictions = {"live": {race_ids[0]: [1, 2, 3], race_ids[1]: [2, 4, 7]}}
    _write_passed_source(source, predictions)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
    )

    assert (
        result["status"]
        == "blocked_pending_frontier_artifact_combo_prior_date_prediction_logic"
    )
    assert result["predictions_by_window"] == {}
    assert not result["selector_diagnostics"][
        "best_selected_current_source_in_all_windows"
    ]
    assert result["recommended_next_action"]["action"] == (
        "implement_locked_best_frontier_artifact_combo_prior_date_prediction_logic"
    )
