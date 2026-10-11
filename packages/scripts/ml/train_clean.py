#!/usr/bin/env python3
"""Train a candidate only from repository-reviewed pre-race source evidence.

clean_model_config.json의 split.train_end까지의 모든 데이터로 단일 모델을
학습하고, 추론 시 재사용 가능한 joblib 번들을 저장한다.

Usage:
    uv run python3 packages/scripts/ml/train_clean.py \\
        --config packages/scripts/autoresearch/clean_model_config.json \\
        --output models/candidate_clean.joblib
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch.parameter_context import (  # noqa: E402
    load_evaluation_parameter_context,
)
from autoresearch.research_clean import (  # noqa: E402
    SNAPSHOT_DIR,
    _build_arrays,
    _build_feature_rows,
    _make_model,
    _normalize_dataset_before_split,
    _normalize_feature_rows_before_split,
    _validate_features,
)
from autoresearch.training_evidence import (  # noqa: E402
    load_reviewed_training_inputs,
)


def _git_commit() -> str | None:
    try:
        repo_root = Path(__file__).resolve().parents[2]
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


def _save_new_bundle(bundle: dict, output_path: Path) -> None:
    """Publish a complete candidate atomically, never replacing an existing file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent, suffix=".joblib", delete=False
        ) as stream:
            temporary_path = Path(stream.name)
            joblib.dump(bundle, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_path, output_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="packages/scripts/autoresearch/clean_model_config.json",
        help="clean_model_config.json 경로",
    )
    parser.add_argument(
        "--output",
        default="models/candidate_clean.joblib",
        help="새 후보 번들 경로 (.joblib); 기존 파일을 교체하지 않음",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    output_path = Path(args.output).absolute()

    inputs = load_reviewed_training_inputs(
        config_path=config_path, artifact_root=SNAPSHOT_DIR
    )
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError(f"Refusing to replace existing model: {output_path}")

    context = load_evaluation_parameter_context(
        config_path=config_path,
        seed_index=0,
        config_bytes=inputs.config_bytes,
    )
    config = dict(context.config)
    model_parameters = context.model_parameters
    features: list[str] = list(config["features"])
    _validate_features(features)

    races, answers = inputs.load_dataset()
    expected_entries = {
        (race["race_id"], horse["chulNo"]) for race in races for horse in race["horses"]
    }
    races, answers, _ = _normalize_dataset_before_split(races, answers)
    rows = _build_feature_rows(races, answers)
    rows, _ = _normalize_feature_rows_before_split(rows)
    actual_entries = {(row["race_id"], row["chulNo"]) for row in rows}
    if actual_entries != expected_entries or len(rows) != len(expected_entries):
        raise ValueError(
            "Training feature construction changed the complete runner field"
        )
    X, y, groups, dates, _ = _build_arrays(rows, features)

    train_end = str(config["split"]["train_end"])
    train_mask = dates <= train_end
    if not train_mask.any():
        raise SystemExit(f"Empty training mask for train_end={train_end}")

    inputs.require_unchanged_implementation()
    model = _make_model(model_parameters)
    sample_weight = np.where(
        y[train_mask] == 1, model_parameters.positive_class_weight, 1.0
    )
    model.fit(X[train_mask], y[train_mask], clf__sample_weight=sample_weight)

    bundle = {
        "pipeline": model,
        "feature_names": features,
        "model_kind": model_parameters.kind,
        "model_params": dict(model_parameters.params),
        "positive_class_weight": float(model_parameters.positive_class_weight),
        "imputer_strategy": model_parameters.imputer_strategy,
        "split": dict(config["split"]),
        "dataset_name": str(config["dataset"]),
        "trained_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "n_train_rows": int(train_mask.sum()),
        "n_train_positive": int(y[train_mask].sum()),
        "n_train_races": int(len({str(g) for g in groups[train_mask]})),
        "config_path": str(config_path),
        "schema_version": "champion-clean-bundle-v1",
        "training_receipt": inputs.receipt(),
        "model_promoted": False,
    }
    inputs.require_unchanged_implementation()
    _save_new_bundle(bundle, output_path)
    summary = {k: v for k, v in bundle.items() if k != "pipeline"}
    print(json.dumps(summary, indent=2, default=str))
    print(f"Saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
