"""Live source-pool overlap2 aggregate materializer tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_live_source_pool_overlap2_aggregate_materializer as materializer,
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
                    "clean_current_best_all_allowed_source_pool_overlap2_aggregate/"
                    "src100/match/rankw0/add0.25/drop0.25/pair0.1/bias0.4"
                ),
                "selector_spec": "add0.25/drop0.25/pair0.1/bias0.4",
                "windows": [
                    {
                        "name": "test",
                        "diagnostics": {
                            "selector": "overlap2_aggregate",
                            "switch_rate": 0.013605,
                            "selection_uses_labels": False,
                        },
                    }
                ],
            },
            "selection_contract": "one_unordered_top3_combo_per_race",
            "source_artifact": "offline-source-meta-extension.json",
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


def test_build_artifact_blocks_when_source_meta_extension_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "overlap2-target.json"
    candidates = tmp_path / "candidates.json"
    missing_source = tmp_path / "missing-source-meta-extension.json"
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
    assert result["selector_diagnostics"]["fallback_only"] is False
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_source_pool_source_meta_extension_source_to_live_runner"
    )
    assert result["policy"]["overlap2_aggregate_must_not_be_treated_as_pass_through"]
    assert not result["counts_as_70_percent_evidence"]


def test_build_artifact_follows_source_meta_extension_child_action(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "overlap2-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "source-meta-extension.json"
    _write_source_target(source_target)
    _write_candidates(candidates, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 0.0, "predicted_race_count": 0},
            "recommended_next_action": {
                "action": "port_locked_best_source_pool_variant_calibration_source_to_live_runner",
                "blocking": False,
                "queue_priority_score": 94.82,
                "reason": "variant calibration source is missing",
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
        "port_locked_best_source_pool_variant_calibration_source_to_live_runner"
    )
    assert result["recommended_next_action"]["upstream_action"] == (
        "port_locked_best_source_pool_overlap2_aggregate_source_to_live_runner"
    )


def test_build_artifact_blocks_when_train_surface_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "overlap2-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "source-meta-extension.json"
    _write_source_target(source_target)
    _write_candidates(candidates, race_count=1)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 1.0, "predicted_race_count": 1},
            "predictions_by_window": {"live": {"r1": [1, 2, 3]}},
            "selection_contract": "one_unordered_top3_combo_per_race",
            "status": "passed",
        },
    )

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
        train_surface_path=tmp_path / "missing-train-surface.json",
    )

    assert result["status"] == (
        "blocked_missing_source_pool_overlap2_aggregate_train_surface"
    )
    assert result["predictions_by_window"] == {}
    assert result["recommended_next_action"]["action"] == (
        "repair_source_pool_overlap2_aggregate_train_surface_before_live_port"
    )


def test_build_artifact_emits_predictions_when_train_surface_is_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_target = tmp_path / "overlap2-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "source-meta-extension.json"
    train_surface = tmp_path / "train-surface.json"
    _write_source_target(source_target)
    race_ids = _write_candidates(candidates, race_count=2)
    _write_json(
        source,
        {
            "coverage": {"coverage_rate": 1.0, "predicted_race_count": 2},
            "predictions_by_window": {
                "live": {
                    race_ids[0]: [1, 2, 3],
                    race_ids[1]: [1, 2, 3],
                }
            },
            "selection_contract": "one_unordered_top3_combo_per_race",
            "status": "passed",
        },
    )
    _write_json(
        train_surface,
        {
            "source_group_spec": "src100/match/rankw0",
            "selector_spec": "add0.25/drop0.25/pair0.1/bias0.4",
        },
    )

    monkeypatch.setattr(
        materializer.source_pool_live,
        "_live_rows_by_race_from_candidate_payload",
        lambda _payload, *, expected_race_ids: {
            race_id: [{"race_id": race_id, "chulNo": 1}] * 3
            for race_id in expected_race_ids
        },
    )
    monkeypatch.setattr(
        materializer,
        "_load_training_state",
        lambda *, train_surface_path, live_race_ids: {
            "surface_payload": {"train_prediction_contract": "safe"},
        },
    )
    monkeypatch.setattr(
        materializer,
        "_predict_live_window",
        lambda **_kwargs: (
            {
                race_ids[0]: [2, 3, 4],
                race_ids[1]: [3, 4, 5],
            },
            {
                "history_update": (
                    "completed_frozen_train_dates_only_no_live_label_updates"
                ),
                "selection_uses_live_labels": False,
            },
        ),
    )

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
        train_surface_path=train_surface,
    )

    assert result["status"] == "passed"
    assert result["diagnostic_only"] is False
    assert result["coverage"]["coverage_rate"] == 1.0
    assert result["coverage"]["predicted_race_count"] == 2
    assert result["predictions_by_window"] == {
        "live": {
            race_ids[0]: [2, 3, 4],
            race_ids[1]: [3, 4, 5],
        }
    }
    assert result["recommended_next_action"]["action"] == (
        "materialize_locked_best_source_pool_ranker_overlap2_from_passed_overlap2_aggregate"
    )
    assert result["selector_diagnostics"]["selection_uses_live_labels"] is False
