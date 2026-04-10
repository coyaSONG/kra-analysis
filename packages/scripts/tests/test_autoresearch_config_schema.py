from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.autoresearch_config_schema import (  # noqa: E402
    AUTORESEARCH_CONFIG_VERSION,
    AutoresearchConfig,
    autoresearch_config_json_schema,
    default_evaluation_contract_payload,
    default_experiment_payload,
    validate_autoresearch_config,
)
from shared.batch_race_selection_policy import (  # noqa: E402
    BATCH_RACE_SELECTION_POLICY_VERSION,
)

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "packages/scripts/autoresearch/clean_model_config.json"


def _build_payload() -> dict:
    return {
        "format_version": AUTORESEARCH_CONFIG_VERSION,
        "dataset": "full_year_2025",
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "rolling_windows": [
            {
                "name": "fold_a",
                "train_end": "20250731",
                "eval_start": "20250801",
                "eval_end": "20250930",
            },
            {
                "name": "fold_b",
                "train_end": "20250930",
                "eval_start": "20251001",
                "eval_end": "20251130",
            },
        ],
        "evaluation_contract": default_evaluation_contract_payload(),
        "model": {
            "kind": "hgb",
            "positive_class_weight": 1.0,
            "params": {"max_depth": 6},
        },
        "experiment": default_experiment_payload(),
        "features": ["rating", "wgBudam"],
        "notes": {"goal": "test"},
    }


def test_autoresearch_config_schema_requires_temporal_and_contract_blocks() -> None:
    schema = autoresearch_config_json_schema()

    assert schema["title"] == "AutoresearchConfig"
    assert "format_version" in schema["required"]
    assert "split" in schema["required"]
    assert "evaluation_contract" in schema["required"]
    assert "experiment" in schema["required"]


def test_autoresearch_config_accepts_current_contract() -> None:
    payload = _build_payload()

    config = AutoresearchConfig.model_validate(payload)

    assert config.split.train_end == "20250930"
    assert config.evaluation_contract.minimum_holdout_race_count == 500
    assert config.evaluation_contract.selection_seed_invariant is True
    assert (
        config.evaluation_contract.batch_target_selection.policy_version
        == BATCH_RACE_SELECTION_POLICY_VERSION
    )
    assert config.experiment.repeat_count == 10
    assert len(config.experiment.evaluation_seeds) == 10


def test_autoresearch_config_rejects_batch_target_selection_override() -> None:
    payload = _build_payload()
    payload["evaluation_contract"]["batch_target_selection"] = {
        **payload["evaluation_contract"]["batch_target_selection"],
        "minimum_active_runners": 4,
    }

    ok, errors = validate_autoresearch_config(payload)

    assert ok is False
    assert any("batch_target_selection" in error for error in errors)


def test_autoresearch_config_rejects_invalid_primary_split_order() -> None:
    payload = _build_payload()
    payload["split"]["test_start"] = "20251101"

    ok, errors = validate_autoresearch_config(payload)

    assert ok is False
    assert any("train_end < dev_end < test_start" in error for error in errors)


def test_autoresearch_config_rejects_incomplete_excluded_replay_statuses() -> None:
    payload = _build_payload()
    payload["evaluation_contract"]["excluded_replay_statuses"] = [
        "late_snapshot_unusable",
        "partial_snapshot",
    ]

    ok, errors = validate_autoresearch_config(payload)

    assert ok is False
    assert any("excluded_replay_statuses" in error for error in errors)


def test_autoresearch_config_rejects_repeat_count_mismatch() -> None:
    payload = _build_payload()
    payload["experiment"]["repeat_count"] = 9

    ok, errors = validate_autoresearch_config(payload)

    assert ok is False
    assert any("repeat_count" in error for error in errors)


def test_autoresearch_config_rejects_dataset_version_mismatch() -> None:
    payload = _build_payload()
    payload["experiment"]["input_data"]["dataset_name"] = "other_dataset"

    ok, errors = validate_autoresearch_config(payload)

    assert ok is False
    assert any("dataset_name" in error for error in errors)


def test_clean_model_config_matches_declared_schema() -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    ok, errors = validate_autoresearch_config(payload)

    assert ok is True, errors
