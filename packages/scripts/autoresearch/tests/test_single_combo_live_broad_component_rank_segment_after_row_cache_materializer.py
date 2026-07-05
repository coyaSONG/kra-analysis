"""Live broad-component rank-segment after-row-cache materializer tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_live_broad_component_rank_segment_after_row_cache_materializer as materializer,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_source_target(path: Path) -> None:
    _write_json(
        path,
        {
            "best": {
                "selector_spec": (
                    "prior_hit2/cur0.3/minsupport1/top3/segrank_support/"
                    "rows5/gains0/shrink0/loss0.25/margin-0.02/maxrank2"
                ),
            },
            "selection_contract": (
                "clean_current_best_plus_broad_component_rank_segment_prior_date_selector"
            ),
            "source_artifact": "offline-row-cache-after-source-pool.json",
        },
    )


def _write_broad_components(path: Path, *, race_count: int = 2) -> list[str]:
    race_ids = [f"r{index}" for index in range(1, race_count + 1)]
    _write_json(
        path,
        {
            "coverage": {
                "expected_race_count": race_count,
                "expected_race_ids": race_ids,
                "status": "passed",
            },
            "materialized_components": ["current"],
            "missing_components": [],
            "predictions_by_window": {"live": {}},
            "status": "passed",
        },
    )
    return race_ids


def test_build_artifact_blocks_when_row_cache_after_source_pool_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "rank-segment-target.json"
    broad_components = tmp_path / "broad-components.json"
    missing_source = tmp_path / "missing-row-cache-after-source-pool.json"
    _write_source_target(source_target)
    _write_broad_components(broad_components)

    result = materializer.build_artifact(
        live_broad_components_path=broad_components,
        live_source_path=missing_source,
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_missing_live_source_artifact"
    assert result["live_source_context"]["status"] == "missing"
    assert result["broad_component_context"]["status"] == "passed"
    assert result["predictions_by_window"] == {}
    assert result["selection_contract"] == (
        "live_current_best_plus_broad_component_rank_segment_prior_date_selector_predictions_by_window"
    )
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner"
    )
    assert result["policy"]["prior_date_history_must_use_completed_prior_dates_only"]
    assert not result["counts_as_70_percent_evidence"]


def test_build_artifact_follows_row_cache_after_source_pool_child_action(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "rank-segment-target.json"
    broad_components = tmp_path / "broad-components.json"
    source = tmp_path / "row-cache-after-source-pool.json"
    _write_source_target(source_target)
    _write_broad_components(broad_components, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 0.0, "predicted_race_count": 0},
            "recommended_next_action": {
                "action": "port_locked_best_source_pool_ranker_overlap2_source_to_live_runner",
                "blocking": False,
                "queue_priority_score": 94.76,
                "reason": "source-pool overlap2 source is missing",
            },
            "status": "blocked_missing_live_source_artifact",
        },
    )

    result = materializer.build_artifact(
        live_broad_components_path=broad_components,
        live_source_path=source,
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_live_source_child_dependency"
    assert result["live_source_context"]["status"] == "failed"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_source_pool_ranker_overlap2_source_to_live_runner"
    )
    assert result["recommended_next_action"]["upstream_action"] == (
        "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner"
    )


def test_build_artifact_blocks_when_train_surface_is_missing(tmp_path: Path) -> None:
    source_target = tmp_path / "rank-segment-target.json"
    broad_components = tmp_path / "broad-components.json"
    source = tmp_path / "row-cache-after-source-pool.json"
    missing_train_surface = tmp_path / "missing-train-surface.json"
    _write_source_target(source_target)
    race_ids = _write_broad_components(broad_components, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 1.0, "predicted_race_count": 1},
            "predictions_by_window": {"live": {race_ids[0]: [1, 2, 3]}},
            "selection_contract": "one_unordered_top3_combo_per_race",
            "status": "passed",
        },
    )

    result = materializer.build_artifact(
        live_broad_components_path=broad_components,
        live_source_path=source,
        source_target_path=source_target,
        train_surface_path=missing_train_surface,
    )

    assert result["status"] == (
        "blocked_missing_broad_component_rank_segment_after_row_cache_train_surface"
    )
    assert result["live_source_context"]["status"] == "passed"
    assert result["train_surface_context"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "repair_broad_component_rank_segment_after_row_cache_train_surface_before_live_port"
    )


def test_build_artifact_emits_rank_segment_live_predictions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_target = tmp_path / "rank-segment-target.json"
    broad_components = tmp_path / "broad-components.json"
    source = tmp_path / "row-cache-after-source-pool.json"
    train_surface = tmp_path / "train-surface.json"
    _write_source_target(source_target)
    race_ids = _write_broad_components(broad_components, race_count=2)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 1.0, "predicted_race_count": 2},
            "predictions_by_window": {
                "live": {
                    race_ids[0]: [1, 2, 3],
                    race_ids[1]: [2, 3, 4],
                }
            },
            "selection_contract": "one_unordered_top3_combo_per_race",
            "status": "passed",
        },
    )
    _write_json(train_surface, {"selector_spec": "stub"})

    def fake_training_state(*, train_surface_path: Path, live_race_ids: list[str]):
        assert train_surface_path == train_surface
        assert live_race_ids == race_ids
        return {
            "component_names": ("component_a",),
            "surface_payload": {
                "train_prediction_contract": (
                    "frozen_prior_date_broad_component_rank_segment"
                )
            },
        }

    def fake_component_predictions(
        path: Path,
        *,
        component_names: tuple[str, ...],
        race_ids: list[str],
    ):
        assert path == broad_components
        assert component_names == ("component_a",)
        return {"component_a": dict.fromkeys(race_ids, (4, 5, 6))}

    def fake_predict_live_window(
        *,
        race_ids: list[str],
        current_best_predictions: dict[str, tuple[int, int, int]],
        component_predictions: dict[str, dict[str, tuple[int, int, int]]],
        train_state: dict[str, object],
    ):
        assert current_best_predictions == {
            race_ids[0]: (1, 2, 3),
            race_ids[1]: (2, 3, 4),
        }
        assert component_predictions["component_a"][race_ids[0]] == (4, 5, 6)
        assert train_state["component_names"] == ("component_a",)
        return (
            {
                race_ids[0]: [1, 2, 3],
                race_ids[1]: [4, 5, 6],
            },
            {
                "history_update": "completed_frozen_train_dates_only_no_live_label_updates",
                "selection_uses_live_labels": False,
            },
        )

    monkeypatch.setattr(materializer, "_load_training_state", fake_training_state)
    monkeypatch.setattr(
        materializer,
        "_load_live_component_predictions",
        fake_component_predictions,
    )
    monkeypatch.setattr(materializer, "_predict_live_window", fake_predict_live_window)

    result = materializer.build_artifact(
        live_broad_components_path=broad_components,
        live_source_path=source,
        source_target_path=source_target,
        train_surface_path=train_surface,
    )

    assert result["status"] == "passed"
    assert result["diagnostic_only"] is False
    assert result["coverage"]["coverage_rate"] == 1.0
    assert result["predictions_by_window"] == {
        "live": {
            race_ids[0]: [1, 2, 3],
            race_ids[1]: [4, 5, 6],
        }
    }
    assert result["selector_diagnostics"]["selection_uses_live_labels"] is False
    assert result["selector_diagnostics"]["live_prediction_diagnostics"][
        "selection_uses_live_labels"
    ] is False
    assert result["recommended_next_action"]["action"] == (
        "materialize_locked_best_row_cache_rank_pattern_after_broad_rank_segment_from_passed_broad_rank_segment"
    )
