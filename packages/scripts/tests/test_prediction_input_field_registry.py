from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prediction_input_schema import PREDICTION_INPUT_NAMES  # noqa: E402
from shared.prerace_field_metadata_schema import TRAIN_INFERENCE_FLAGS  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "data/contracts/prediction_input_field_registry_v1.csv"
CONFIG_PATH = ROOT / "packages/scripts/autoresearch/clean_model_config.json"
ALLOWED_RUNTIME_FLAGS = {"ALLOW", "ALLOW_SNAPSHOT_ONLY", "ALLOW_STORED_ONLY"}
EXPECTED_HOLD_FIELDS = {"winOdds", "plcOdds", "odds_rank", "winOdds_rr", "plcOdds_rr"}


def _load_registry_rows() -> list[dict[str, str]]:
    with REGISTRY_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_registry_covers_every_safe_feature_once():
    rows = _load_registry_rows()
    safe_features = list(PREDICTION_INPUT_NAMES)

    assert len(rows) == len(safe_features)

    registry_names = [row["prediction_input_name"] for row in rows]
    assert len(registry_names) == len(set(registry_names))
    assert set(registry_names) == set(safe_features)


def test_registry_uses_only_declared_flags_and_expected_hold_fields():
    rows = _load_registry_rows()
    seen_flags = {row["train_inference_flag"] for row in rows}

    assert seen_flags <= set(TRAIN_INFERENCE_FLAGS)

    hold_fields = {
        row["prediction_input_name"]
        for row in rows
        if row["train_inference_flag"] == "HOLD"
    }
    assert hold_fields == EXPECTED_HOLD_FIELDS


def test_clean_model_config_uses_only_operational_fields():
    rows = _load_registry_rows()
    registry = {row["prediction_input_name"]: row for row in rows}
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    config_features = config["features"]
    assert config_features

    for feature in config_features:
        assert feature in registry, f"{feature} missing from prediction input registry"
        assert registry[feature]["train_inference_flag"] in ALLOWED_RUNTIME_FLAGS
