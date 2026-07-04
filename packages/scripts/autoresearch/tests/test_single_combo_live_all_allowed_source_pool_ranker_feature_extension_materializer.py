"""Live feature-extended source-pool ranker materializer tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_live_all_allowed_source_pool_ranker_feature_extension_materializer as materializer,
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
                    "clean_current_best_all_allowed_source_pool_ranker/"
                    "src200/exact/rankw0/hgb/rows1000/pos40/"
                    "cur0.25/srcw0/ovw0.05/minp0/margin0"
                ),
                "model_spec": "hgb/rows1000/pos40",
                "selector_spec": "cur0.25/srcw0/ovw0.05/minp0/margin0",
                "source_group_spec": "src200/exact/rankw0",
                "summary": {
                    "overfit_safe_exact_rate": 0.538462,
                    "test_exact_3of3_rate": 0.564626,
                },
                "windows": [
                    {
                        "name": "test",
                        "diagnostics": {
                            "model_fit": True,
                            "selection_uses_labels": False,
                            "switch_rate": 0.054422,
                        },
                    }
                ],
            },
            "selection_contract": "one_unordered_top3_combo_per_race",
            "source_artifact": "offline-row-cache-prior-date.json",
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


def test_build_artifact_blocks_when_row_cache_source_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "feature-extension-target.json"
    candidates = tmp_path / "candidates.json"
    _write_source_target(source_target)
    _write_candidates(candidates)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=tmp_path / "missing-row-cache.json",
        source_target_path=source_target,
    )

    assert result["status"] == "blocked_missing_live_source_artifact"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_row_cache_rank_pattern_prior_date_source_to_live_runner"
    )
    assert result["predictions_by_window"] == {}
    assert result["selector_diagnostics"]["selector"] == (
        "source_pool_ranker_feature_extension_prior_date"
    )


def test_build_artifact_blocks_when_train_surface_is_missing(
    tmp_path: Path,
) -> None:
    source_target = tmp_path / "feature-extension-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "row-cache-source.json"
    _write_source_target(source_target)
    race_ids = _write_candidates(candidates, race_count=2)
    _write_passed_source(source, race_ids)

    result = materializer.build_artifact(
        candidate_features_path=candidates,
        live_source_path=source,
        source_target_path=source_target,
        train_surface_path=tmp_path / "missing-train-surface.json",
    )

    assert (
        result["status"]
        == "blocked_missing_all_allowed_source_pool_ranker_feature_extension_train_surface"
    )
    assert result["recommended_next_action"]["action"] == (
        "repair_all_allowed_source_pool_ranker_feature_extension_train_surface_before_live_port"
    )
    assert result["predictions_by_window"] == {}


def test_build_artifact_emits_feature_extension_predictions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_target = tmp_path / "feature-extension-target.json"
    candidates = tmp_path / "candidates.json"
    source = tmp_path / "row-cache-source.json"
    train_surface = tmp_path / "train-surface.json"
    _write_source_target(source_target)
    race_ids = _write_candidates(candidates, race_count=2)
    _write_passed_source(source, race_ids)
    _write_json(
        train_surface,
        {
            "source_group_spec": "src200/exact/rankw0",
            "model_spec": "hgb/rows1000/pos40",
            "selector_spec": "cur0.25/srcw0/ovw0.05/minp0/margin0",
        },
    )

    monkeypatch.setattr(
        materializer.base_materializer,
        "_live_rows_by_race_from_candidate_payload",
        lambda _payload, *, expected_race_ids: {
            race_id: [{"race_id": race_id, "chulNo": 1}] * 3
            for race_id in expected_race_ids
        },
    )
    monkeypatch.setattr(
        materializer.base_materializer,
        "_load_training_state",
        lambda *, candidate_rows_builder, train_surface_path, live_race_ids: {
            "surface_payload": {"train_prediction_contract": "safe"},
            "train_candidate_rows": 10,
        },
    )
    monkeypatch.setattr(
        materializer.base_materializer,
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
    assert result["predictions_by_window"]["live"][race_ids[0]] == [2, 3, 4]
    assert result["feature_extension"]["adds_horse_pair_aggregates"]
    assert result["recommended_next_action"]["action"] == (
        "materialize_locked_best_source_pool_variant_calibration_from_passed_feature_extension_ranker"
    )
    assert not result["policy"]["hgb_model_prediction_logic_must_be_ported_before_emit"]
