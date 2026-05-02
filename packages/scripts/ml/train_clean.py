#!/usr/bin/env python3
"""Production trainer for the autoresearch leakage-free champion model.

clean_model_config.json의 split.train_end까지의 모든 데이터로 단일 모델을
학습하고, 추론 시 재사용 가능한 joblib 번들을 저장한다.

Usage:
    uv run python3 packages/scripts/ml/train_clean.py \\
        --config packages/scripts/autoresearch/clean_model_config.json \\
        --output models/champion_clean.joblib
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch.dataset_artifacts import resolve_offline_evaluation_dataset_artifacts  # noqa: E402
from autoresearch.parameter_context import load_evaluation_parameter_context  # noqa: E402
from autoresearch.research_clean import (  # noqa: E402
    SNAPSHOT_DIR,
    _build_arrays,
    _build_feature_rows,
    _load_dataset,
    _make_model,
    _normalize_dataset_before_split,
    _normalize_feature_rows_before_split,
    _validate_features,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="packages/scripts/autoresearch/clean_model_config.json",
        help="clean_model_config.json 경로",
    )
    parser.add_argument(
        "--output",
        default="models/champion_clean.joblib",
        help="출력 번들 경로 (.joblib)",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    context = load_evaluation_parameter_context(
        config_path=config_path,
        seed_index=0,
    )
    config = dict(context.config)
    model_parameters = context.model_parameters
    features: list[str] = list(config["features"])
    _validate_features(features)

    dataset_artifacts = resolve_offline_evaluation_dataset_artifacts(
        str(config["dataset"]),
        artifact_root=SNAPSHOT_DIR,
    )
    races, answers = _load_dataset(dataset_artifacts)
    races, answers, _ = _normalize_dataset_before_split(races, answers)
    rows = _build_feature_rows(races, answers)
    rows, _ = _normalize_feature_rows_before_split(rows)
    X, y, groups, dates, _ = _build_arrays(rows, features)

    train_end = str(config["split"]["train_end"])
    train_mask = dates <= train_end
    if not train_mask.any():
        raise SystemExit(f"Empty training mask for train_end={train_end}")

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
    }
    joblib.dump(bundle, output_path)
    summary = {k: v for k, v in bundle.items() if k != "pipeline"}
    print(json.dumps(summary, indent=2, default=str))
    print(f"Saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
