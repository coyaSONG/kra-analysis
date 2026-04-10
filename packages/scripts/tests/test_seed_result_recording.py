from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.execution_matrix import (  # noqa: E402
    SeedExecutionMetrics,
    build_model_config_id,
)
from shared.seed_result_recording import (  # noqa: E402
    DetailedSeedResultRecord,
    build_detailed_seed_result_repository,
    upsert_detailed_seed_result_record,
    validate_detailed_seed_result_record_payload,
    validate_detailed_seed_result_repository_payload,
)


def _build_record(
    *, run_id: str, seed_index: int, seed: int
) -> DetailedSeedResultRecord:
    return DetailedSeedResultRecord(
        run_id=run_id,
        task_id=f"task-{seed_index:02d}",
        seed=seed,
        seed_index=seed_index,
        run_at="2026-04-11T12:00:00+09:00",
        model_config_id=build_model_config_id(
            {"dataset": "holdout", "model": {"kind": "hgb", "params": {"max_depth": 6}}}
        ),
        split_settings={
            "dataset": "holdout",
            "split": {
                "train_end": "20250930",
                "dev_end": "20251130",
                "test_start": "20251201",
            },
            "evaluation_contract": {
                "selection_method": "time_ordered_complete_date_accumulation",
                "target_label": "unordered_top3",
            },
        },
        search_parameters={
            "experiment_profile_version": "autoresearch-experiment-profile-v1",
            "repeat_count": 10,
            "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61],
            "model_search_strategy": "curated_candidates_v1",
            "candidate_names": ["baseline_hgb_depth6_lr005"],
            "candidate_count": 1,
            "model_candidates": [
                {
                    "name": "baseline_hgb_depth6_lr005",
                    "kind": "hgb",
                    "params": {"max_depth": 6},
                }
            ],
            "common_hyperparameters": {
                "positive_class_weight": 1.0,
                "imputer_strategy": "median",
                "prediction_top_k": 3,
            },
            "resolved_model_parameters": {
                "candidate_name": "baseline_hgb_depth6_lr005",
                "kind": "hgb",
                "params": {"max_depth": 6},
                "positive_class_weight": 1.0,
                "imputer_strategy": "median",
                "prediction_top_k": 3,
                "random_state": seed,
                "random_state_source": "evaluation_seed",
            },
            "parameter_source": "config.experiment.evaluation_seeds",
            "model_parameter_source": "config.experiment.common_hyperparameters",
        },
        seed_context={
            "run_id": run_id,
            "seed_index": seed_index,
            "model_random_state": seed,
            "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61],
            "parameter_source": "config.experiment.evaluation_seeds",
            "selection_seed_invariant": True,
        },
        evaluation_result={
            "summary": {"overfit_safe_exact_rate": 0.71, "robust_exact_rate": 0.73},
            "dev": {"exact_3of3_rate": 0.7},
            "test": {"exact_3of3_rate": 0.72},
            "core_metrics": SeedExecutionMetrics(
                overfit_safe_exact_rate=0.71,
                robust_exact_rate=0.73,
                test_exact_3of3_rate=0.72,
            ).model_dump(mode="json"),
            "overall_holdout_hit_rate": 0.71,
            "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
        },
        artifacts={
            "output_path": f"/tmp/{run_id}.json",
            "manifest_path": f"/tmp/{run_id}_manifest.json",
            "config_path": "/tmp/config.json",
        },
    )


def test_detailed_seed_result_record_validates_expected_sections() -> None:
    record = _build_record(run_id="seed_01_rs11", seed_index=1, seed=11)

    payload = record.model_dump(mode="json")
    ok, errors = validate_detailed_seed_result_record_payload(payload)

    assert ok is True, errors
    assert payload["split_settings"]["dataset"] == "holdout"
    assert payload["search_parameters"]["candidate_count"] == 1
    assert payload["seed_context"]["model_random_state"] == 11
    assert payload["evaluation_result"]["overall_holdout_hit_rate"] == 0.71


def test_detailed_seed_result_repository_upsert_tracks_missing_runs() -> None:
    repository = build_detailed_seed_result_repository(
        group_id="holdout-10seed",
        evaluation_seeds=(11, 17, 23, 31, 37, 41, 47, 53, 59, 61),
    )

    repository = upsert_detailed_seed_result_record(
        repository,
        _build_record(run_id="seed_01_rs11", seed_index=1, seed=11),
        group_id="holdout-10seed",
        evaluation_seeds=(11, 17, 23, 31, 37, 41, 47, 53, 59, 61),
    )

    payload = repository.model_dump(mode="json")
    ok, errors = validate_detailed_seed_result_repository_payload(payload)

    assert ok is True, errors
    assert payload["summary"]["recorded_run_count"] == 1
    assert payload["summary"]["missing_run_ids"][0] == "seed_02_rs17"
    assert payload["summary"]["lowest_overall_holdout_hit_rate"] == 0.71
