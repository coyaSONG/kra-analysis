from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.reproducibility_manifest_schema import (  # noqa: E402
    validate_reproducibility_manifest,
)

from autoresearch.dataset_artifacts import (  # noqa: E402
    resolve_offline_evaluation_dataset_artifacts,
)
from autoresearch.holdout_dataset import build_dataset_manifest  # noqa: E402
from autoresearch.parameter_context import (
    resolve_evaluation_model_parameters,  # noqa: E402
)
from autoresearch.reproducibility import (  # noqa: E402
    build_research_evaluation_manifest,
    manifest_path_for_output,
    metrics_artifact_path_for_output,
    model_random_state_for_config,
    prediction_artifact_path_for_output,
    write_research_evaluation_bundle,
)
from autoresearch.research_clean import (  # noqa: E402
    _make_model,
    load_runtime_params,
)


def _snapshot_meta(*, race_id: str, race_date: str = "20250101") -> dict:
    entry_finalized_at = "2025-01-01T10:35:00+09:00"
    return {
        "race_id": race_id,
        "format_version": "holdout-snapshot-v1",
        "rule_version": "holdout-entry-finalization-rule-v1",
        "source_filter_basis": "entry_finalized_at",
        "scheduled_start_at": "2025-01-01T11:00:00+09:00",
        "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
        "snapshot_ready_at": entry_finalized_at,
        "entry_finalized_at": entry_finalized_at,
        "selected_timestamp_field": "basic_data.collected_at",
        "selected_timestamp_value": entry_finalized_at,
        "timestamp_source": "snapshot_collected_at",
        "timestamp_confidence": "medium",
        "revision_id": None,
        "late_reissue_after_cutoff": False,
        "cutoff_unbounded": False,
        "replay_status": "strict",
        "include_in_strict_dataset": True,
        "hard_required_sources_present": True,
        "hard_required_source_status": {
            "API214_1": "present",
            "API72_2": "present",
            "API189_1": "present",
            "API9_1": "present",
        },
        "source_lookup": {
            "race_id": race_id,
            "race_date": race_date,
            "entry_snapshot_at": entry_finalized_at,
        },
    }


def _write_dataset_manifest(snapshot_dir: Path, *, dataset: str, race_id: str) -> None:
    (snapshot_dir / f"{dataset}_manifest.json").write_text(
        json.dumps(
            build_dataset_manifest(
                mode=dataset,
                created_at="2026-04-10T12:00:00+09:00",
                races=[_snapshot_meta(race_id=race_id)],
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _race_payload(*, race_id: str) -> dict:
    return {
        "race_id": race_id,
        "race_date": "20250101",
        "meet": "서울",
        "race_info": {
            "rcDate": "20250101",
            "rcNo": "1",
            "rcDist": 1200,
            "track": "건조",
            "weather": "맑음",
            "meet": "서울",
        },
        "horses": [
            {"chulNo": 1, "hrName": "테스트마1"},
            {"chulNo": 2, "hrName": "테스트마2"},
            {"chulNo": 3, "hrName": "테스트마3"},
        ],
        "snapshot_meta": _snapshot_meta(race_id=race_id),
    }


def test_model_random_state_for_config_returns_fixed_seed() -> None:
    assert model_random_state_for_config({"model": {"kind": "hgb"}}) == 42
    assert model_random_state_for_config({"model": {"kind": "rf"}}) == 42
    assert model_random_state_for_config({"model": {"kind": "et"}}) == 42
    assert model_random_state_for_config({"model": {"kind": "logreg"}}) is None


def test_load_runtime_params_rejects_mismatched_external_seed_override(
    tmp_path: Path,
) -> None:
    config = {
        "dataset": "full_year_2025",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
        "features": ["rating"],
    }
    runtime_params_path = tmp_path / "runtime_params.json"
    runtime_params_path.write_text(
        json.dumps({"model_random_state": 17}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    runtime_params = load_runtime_params(
        config=config,
        runtime_params_path=runtime_params_path,
    )

    assert runtime_params == {"model_random_state": 17}
    with pytest.raises(
        ValueError,
        match="runtime_params_path.model_random_state and model_random_state must match",
    ):
        load_runtime_params(
            config=config,
            runtime_params_path=runtime_params_path,
            model_random_state=23,
        )


def test_make_model_uses_runtime_seed_for_fixed_model_config() -> None:
    config = {
        "model": {
            "kind": "hgb",
            "params": {
                "max_depth": 6,
                "learning_rate": 0.05,
                "max_iter": 600,
                "min_samples_leaf": 30,
                "l2_regularization": 0.4,
            },
        }
    }

    model_parameters, _source = resolve_evaluation_model_parameters(
        config,
        model_random_state=29,
    )
    model = _make_model(model_parameters)

    assert model.named_steps["clf"].random_state == 29


def test_build_research_evaluation_manifest_includes_source_version_and_hashes(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "full_year_2025.json").write_text(
        json.dumps([_race_payload(race_id="race-1")], ensure_ascii=False),
        encoding="utf-8",
    )
    (snapshot_dir / "full_year_2025_answer_key.json").write_text(
        json.dumps({"race-1": [1, 2, 3]}, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_dataset_manifest(snapshot_dir, dataset="full_year_2025", race_id="race-1")

    config = {
        "dataset": "full_year_2025",
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
        "features": ["rating"],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    output_path = tmp_path / "research_clean.json"
    output_payload = json.dumps(
        {"summary": {"robust_exact_rate": 0.7}}, ensure_ascii=False, indent=2
    )
    runtime_params_path = tmp_path / "runtime_params.json"
    runtime_params_path.write_text(
        json.dumps({"model_random_state": 17}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = build_research_evaluation_manifest(
        config_path=config_path,
        config=config,
        output_path=output_path,
        output_payload=output_payload,
        created_at="2026-04-10T12:00:00+09:00",
        dataset_artifacts=resolve_offline_evaluation_dataset_artifacts(
            "full_year_2025",
            artifact_root=snapshot_dir,
        ),
        runtime_params_path=runtime_params_path,
        runtime_params={"model_random_state": 17},
    )

    payload = manifest.model_dump(mode="json")
    ok, errors = validate_reproducibility_manifest(payload)
    assert ok is True, errors
    assert payload["source_data"]["dataset"] == "full_year_2025"
    assert payload["source_data"]["version_id"].startswith("dataset-source-v1:")
    assert payload["configuration"]["settings"]["split"]["train_end"] == "20250930"
    assert payload["seeds"]["model_random_state"] == 17
    assert payload["run_created_at"] == "2026-04-10T12:00:00+09:00"
    assert {item["artifact_id"] for item in payload["artifacts"]} == {
        "evaluation_config",
        "evaluation_runtime_params",
        "dataset_snapshot",
        "dataset_answer_key",
        "dataset_manifest",
        "evaluation_result",
    }
    assert payload["split"] is None
    assert payload["manifest_sha256"]


def test_build_research_evaluation_manifest_reads_and_validates_execution_matrix_seed_block(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "holdout.json").write_text(
        json.dumps([_race_payload(race_id="race-1")], ensure_ascii=False),
        encoding="utf-8",
    )
    (snapshot_dir / "holdout_answer_key.json").write_text(
        json.dumps({"race-1": [1, 2, 3]}, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_dataset_manifest(snapshot_dir, dataset="holdout", race_id="race-1")

    config = {
        "dataset": "holdout",
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
        "features": ["rating"],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (tmp_path / "holdout_split_manifest.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "seed": {
                        "selection_seed": None,
                        "selection_seed_invariant": True,
                        "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61],
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = build_research_evaluation_manifest(
        config_path=config_path,
        config=config,
        output_path=tmp_path / "research_clean.json",
        output_payload=json.dumps(
            {"summary": {"robust_exact_rate": 0.7}}, ensure_ascii=False, indent=2
        ),
        created_at="2026-04-10T12:00:00+09:00",
        dataset_artifacts=resolve_offline_evaluation_dataset_artifacts(
            "holdout",
            artifact_root=snapshot_dir,
        ),
        runtime_params={"model_random_state": 17},
    )

    assert manifest.seeds.evaluation_seeds == (11, 17, 23, 31, 37, 41, 47, 53, 59, 61)
    assert manifest.split is not None
    assert manifest.split.artifact_id == "dataset_split_manifest"
    assert manifest.split.manifest_path == str(tmp_path / "holdout_split_manifest.json")
    assert manifest.split.included_race_count is None
    assert manifest.split.evaluation_seeds == (11, 17, 23, 31, 37, 41, 47, 53, 59, 61)


def test_build_research_evaluation_manifest_rejects_invalid_execution_matrix_seed_block(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "holdout.json").write_text(
        json.dumps([_race_payload(race_id="race-1")], ensure_ascii=False),
        encoding="utf-8",
    )
    (snapshot_dir / "holdout_answer_key.json").write_text(
        json.dumps({"race-1": [1, 2, 3]}, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_dataset_manifest(snapshot_dir, dataset="holdout", race_id="race-1")

    config = {
        "dataset": "holdout",
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
        "features": ["rating"],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (tmp_path / "holdout_split_manifest.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "seed": {
                        "selection_seed": None,
                        "selection_seed_invariant": True,
                        "evaluation_seeds": [11, 17, 23],
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        build_research_evaluation_manifest(
            config_path=config_path,
            config=config,
            output_path=tmp_path / "research_clean.json",
            output_payload=json.dumps(
                {"summary": {"robust_exact_rate": 0.7}}, ensure_ascii=False, indent=2
            ),
            created_at="2026-04-10T12:00:00+09:00",
            dataset_artifacts=resolve_offline_evaluation_dataset_artifacts(
                "holdout",
                artifact_root=snapshot_dir,
            ),
            runtime_params={"model_random_state": 17},
        )
    except ValueError as exc:
        assert "정확히 10개" in str(exc)
    else:
        raise AssertionError("invalid execution matrix seed block should fail")


def test_write_research_evaluation_bundle_persists_companion_manifest(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "full_year_2025.json").write_text(
        json.dumps([_race_payload(race_id="race-1")], ensure_ascii=False),
        encoding="utf-8",
    )
    (snapshot_dir / "full_year_2025_answer_key.json").write_text(
        json.dumps({"race-1": [1, 2, 3]}, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_dataset_manifest(snapshot_dir, dataset="full_year_2025", race_id="race-1")

    config = {
        "dataset": "full_year_2025",
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
        "features": ["rating"],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    result = {"summary": {"robust_exact_rate": 0.7123}}
    output_path = tmp_path / "research_clean.json"
    runtime_params_path = tmp_path / "runtime_params.json"
    runtime_params_path.write_text(
        json.dumps({"model_random_state": 19}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    written_output, written_manifest = write_research_evaluation_bundle(
        result={
            **result,
            "_reproducibility_artifacts": {
                "prediction_rows": {
                    "format_version": "research-evaluation-prediction-rows-v1",
                    "dataset": "full_year_2025",
                    "windows": [
                        {
                            "name": "test",
                            "train_end": "20250930",
                            "eval_start": "20251201",
                            "eval_end": None,
                            "summary": {"exact_3of3_rate": 0.7123},
                            "prediction_rows": [
                                {
                                    "race_id": "race-1",
                                    "predicted_top3_unordered": [1, 2, 3],
                                    "actual_top3_unordered": [1, 2, 3],
                                    "hit_count": 3,
                                    "exact_match": True,
                                }
                            ],
                        }
                    ],
                },
                "metrics_summary": {
                    "format_version": "research-evaluation-metrics-v1",
                    "dataset": "full_year_2025",
                    "feature_count": 1,
                    "market_feature_count": 0,
                    "integrity": {},
                    "summary": {"robust_exact_rate": 0.7123},
                    "dev": {"exact_3of3_rate": 0.7},
                    "test": {"exact_3of3_rate": 0.7123},
                    "rolling": [],
                },
            },
        },
        config_path=config_path,
        output_path=output_path,
        created_at=datetime.fromisoformat("2026-04-10T12:00:00+09:00"),
        dataset_artifacts=resolve_offline_evaluation_dataset_artifacts(
            "full_year_2025",
            artifact_root=snapshot_dir,
        ),
        runtime_params_path=runtime_params_path,
        runtime_params={"model_random_state": 19},
    )

    assert written_output == output_path
    assert written_manifest == manifest_path_for_output(output_path)
    assert written_output.exists() is True
    assert written_manifest.exists() is True
    assert prediction_artifact_path_for_output(output_path).exists() is True
    assert metrics_artifact_path_for_output(output_path).exists() is True

    payload = json.loads(written_manifest.read_text(encoding="utf-8"))
    ok, errors = validate_reproducibility_manifest(payload)
    assert ok is True, errors
    assert {item["artifact_id"] for item in payload["artifacts"]} == {
        "evaluation_config",
        "evaluation_runtime_params",
        "dataset_snapshot",
        "dataset_answer_key",
        "dataset_manifest",
        "evaluation_prediction_rows",
        "evaluation_metrics_summary",
        "evaluation_result",
    }
    assert payload["artifacts"][-1]["artifact_id"] == "evaluation_result"
    assert payload["artifacts"][-1]["generated_at"] == "2026-04-10T12:00:00+09:00"
    assert payload["seeds"]["model_random_state"] == 19
    persisted_output = json.loads(written_output.read_text(encoding="utf-8"))
    assert "_reproducibility_artifacts" not in persisted_output
    prediction_payload = json.loads(
        prediction_artifact_path_for_output(output_path).read_text(encoding="utf-8")
    )
    assert prediction_payload["windows"][0]["prediction_rows"][0]["race_id"] == "race-1"
    metrics_payload = json.loads(
        metrics_artifact_path_for_output(output_path).read_text(encoding="utf-8")
    )
    assert metrics_payload["summary"]["robust_exact_rate"] == 0.7123
