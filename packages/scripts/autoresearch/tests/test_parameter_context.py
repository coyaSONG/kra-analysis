from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoresearch.parameter_context import (
    load_evaluation_parameter_context,  # noqa: E402
    load_seed_matrix_parameter_context,
)


def test_load_evaluation_parameter_context_resolves_seed_from_config_experiment(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "dataset": "holdout",
                "model": {"kind": "hgb", "params": {"max_depth": 6}},
                "experiment": {
                    "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61]
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    context = load_evaluation_parameter_context(
        config_path=config_path,
        seed_index=2,
        run_id="seed_02_rs17",
    )

    assert context.parameter_source == "config.experiment.evaluation_seeds"
    assert context.evaluation_seeds == (11, 17, 23, 31, 37, 41, 47, 53, 59, 61)
    assert context.runtime_params.model_random_state == 17
    assert context.model_parameters.kind == "hgb"
    assert context.model_parameters.random_state == 17
    assert context.model_parameter_source == "parameter_context.fallback"
    assert context.input_contract is None
    assert context.input_contract_signature is None


def test_load_evaluation_parameter_context_rejects_runtime_override_mismatch(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    runtime_params_path = tmp_path / "runtime_params.json"
    config_path.write_text(
        json.dumps(
            {
                "dataset": "holdout",
                "model": {"kind": "hgb", "params": {"max_depth": 6}},
                "experiment": {
                    "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61]
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    runtime_params_path.write_text(
        json.dumps({"model_random_state": 99}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="config.experiment.evaluation_seeds must remain authoritative",
    ):
        load_evaluation_parameter_context(
            config_path=config_path,
            seed_index=2,
            run_id="seed_02_rs17",
            runtime_params_path=runtime_params_path,
        )


def test_load_evaluation_parameter_context_injects_model_search_hyperparameters(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "format_version": "autoresearch-clean-config-v1",
                "dataset": "holdout",
                "split": {
                    "train_end": "20250930",
                    "dev_end": "20251130",
                    "test_start": "20251201",
                },
                "evaluation_contract": {
                    "same_source_data_required": True,
                    "selection_method": "time_ordered_complete_date_accumulation",
                    "boundary_unit": "race_date",
                    "minimum_holdout_race_count": 500,
                    "minimum_mini_val_race_count": 200,
                    "require_complete_race_dates": True,
                    "allow_intra_day_cut": False,
                    "selection_seed_invariant": True,
                    "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
                    "target_label": "unordered_top3",
                    "holdout_rule_version": "recent-holdout-split-rule-v1",
                    "entry_finalization_rule_version": "holdout-entry-finalization-rule-v1",
                    "strict_dataset_selector": "include_in_strict_dataset_true",
                    "excluded_replay_statuses": [
                        "late_snapshot_unusable",
                        "missing_timestamp",
                        "partial_snapshot",
                    ],
                    "excluded_race_reasons": [
                        "insufficient_active_runners",
                        "invalid_top3_result",
                        "late_snapshot_unusable",
                        "leakage_violation",
                        "missing_basic_data",
                        "missing_result_data",
                        "partial_snapshot",
                        "payload_conversion_failed",
                        "top3_not_in_active_runners",
                    ],
                },
                "model": {
                    "kind": "hgb",
                    "positive_class_weight": 1.0,
                    "params": {
                        "max_depth": 6,
                        "learning_rate": 0.05,
                        "max_iter": 600,
                        "min_samples_leaf": 30,
                        "l2_regularization": 0.4,
                    },
                },
                "features": ["rating"],
                "experiment": {
                    "profile_version": "autoresearch-experiment-profile-v1",
                    "repeat_count": 10,
                    "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61],
                    "input_data": {
                        "dataset_name": "holdout",
                        "version_id": "holdout-v1",
                        "source_policy_version": "prerace-entry-finalized-only-v1",
                        "feature_schema_version": "alternative-ranking-input-v1",
                        "operational_snapshot_only": True,
                    },
                    "model_search": {
                        "strategy": "curated_candidates_v1",
                        "candidates": [
                            {
                                "name": "baseline_hgb_depth6_lr005",
                                "kind": "hgb",
                                "params": {
                                    "max_depth": 6,
                                    "learning_rate": 0.05,
                                    "max_iter": 600,
                                    "min_samples_leaf": 30,
                                    "l2_regularization": 0.4,
                                },
                            }
                        ],
                    },
                    "common_hyperparameters": {
                        "positive_class_weight": 1.0,
                        "imputer_strategy": "median",
                        "random_state_source": "evaluation_seed",
                        "target_label": "unordered_top3",
                        "prediction_top_k": 3,
                    },
                },
                "notes": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    context = load_evaluation_parameter_context(
        config_path=config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )

    assert context.model_parameters.candidate_name == "baseline_hgb_depth6_lr005"
    assert context.model_parameters.positive_class_weight == 1.0
    assert context.model_parameters.imputer_strategy == "median"
    assert context.model_parameters.prediction_top_k == 3
    assert context.model_parameters.random_state == 11
    assert context.model_parameter_source == "config.experiment.common_hyperparameters"
    assert context.input_contract is not None
    assert (
        context.input_contract.format_version
        == "autoresearch-evaluation-input-contract-v1"
    )
    assert context.input_contract.dataset == "holdout"
    assert context.input_contract.split.train_end == "20250930"
    assert context.input_contract.selected_run is not None
    assert context.input_contract.selected_run.run_id == "seed_01_rs11"
    assert context.input_contract.selected_run.model_random_state == 11
    assert context.input_contract.execution_matrix.evaluation_seeds == (
        11,
        17,
        23,
        31,
        37,
        41,
        47,
        53,
        59,
        61,
    )
    assert context.input_contract_signature is not None


def test_load_seed_matrix_parameter_context_prefers_config_seeds_and_injected_defaults(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "experiment": {
                    "evaluation_seeds": [71, 73, 79, 83, 89, 97, 101, 103, 107, 109]
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    context = load_seed_matrix_parameter_context(
        config_path=config_path,
        max_workers=4,
    )

    assert context.runtime_params.evaluation_seeds == (
        71,
        73,
        79,
        83,
        89,
        97,
        101,
        103,
        107,
        109,
    )
    assert context.runtime_params.group_id
    assert context.runtime_params.max_workers == 4
    assert context.evaluation_seed_source == "config.experiment.evaluation_seeds"
    assert context.group_id_source == "execution_matrix.default_group_id"
    assert context.max_workers_source == "cli.max_workers"
    assert context.execution_matrix is None


def test_load_seed_matrix_parameter_context_builds_execution_matrix_for_validated_config(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "format_version": "autoresearch-clean-config-v1",
                "dataset": "holdout",
                "split": {
                    "train_end": "20250930",
                    "dev_end": "20251130",
                    "test_start": "20251201",
                },
                "evaluation_contract": {
                    "same_source_data_required": True,
                    "selection_method": "time_ordered_complete_date_accumulation",
                    "boundary_unit": "race_date",
                    "minimum_holdout_race_count": 500,
                    "minimum_mini_val_race_count": 200,
                    "require_complete_race_dates": True,
                    "allow_intra_day_cut": False,
                    "selection_seed_invariant": True,
                    "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
                    "target_label": "unordered_top3",
                    "holdout_rule_version": "recent-holdout-split-rule-v1",
                    "entry_finalization_rule_version": "holdout-entry-finalization-rule-v1",
                    "strict_dataset_selector": "include_in_strict_dataset_true",
                    "excluded_replay_statuses": [
                        "late_snapshot_unusable",
                        "missing_timestamp",
                        "partial_snapshot",
                    ],
                    "excluded_race_reasons": [
                        "insufficient_active_runners",
                        "invalid_top3_result",
                        "late_snapshot_unusable",
                        "leakage_violation",
                        "missing_basic_data",
                        "missing_result_data",
                        "partial_snapshot",
                        "payload_conversion_failed",
                        "top3_not_in_active_runners",
                    ],
                },
                "model": {
                    "kind": "hgb",
                    "positive_class_weight": 1.0,
                    "params": {
                        "max_depth": 6,
                        "learning_rate": 0.05,
                        "max_iter": 600,
                        "min_samples_leaf": 30,
                        "l2_regularization": 0.4,
                    },
                },
                "features": ["rating"],
                "experiment": {
                    "profile_version": "autoresearch-experiment-profile-v1",
                    "repeat_count": 10,
                    "evaluation_seeds": [71, 73, 79, 83, 89, 97, 101, 103, 107, 109],
                    "input_data": {
                        "dataset_name": "holdout",
                        "version_id": "holdout-v1",
                        "source_policy_version": "prerace-entry-finalized-only-v1",
                        "feature_schema_version": "alternative-ranking-input-v1",
                        "operational_snapshot_only": True,
                    },
                    "model_search": {
                        "strategy": "curated_candidates_v1",
                        "candidates": [
                            {
                                "name": "baseline_hgb_depth6_lr005",
                                "kind": "hgb",
                                "params": {
                                    "max_depth": 6,
                                    "learning_rate": 0.05,
                                    "max_iter": 600,
                                    "min_samples_leaf": 30,
                                    "l2_regularization": 0.4,
                                },
                            }
                        ],
                    },
                    "common_hyperparameters": {
                        "positive_class_weight": 1.0,
                        "imputer_strategy": "median",
                        "random_state_source": "evaluation_seed",
                        "target_label": "unordered_top3",
                        "prediction_top_k": 3,
                    },
                },
                "notes": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    context = load_seed_matrix_parameter_context(
        config_path=config_path,
        max_workers=2,
    )

    assert context.execution_matrix is not None
    assert context.execution_matrix.evaluation_seeds == (
        71,
        73,
        79,
        83,
        89,
        97,
        101,
        103,
        107,
        109,
    )
    assert context.execution_matrix.holdout.selection_seed_invariant is True
