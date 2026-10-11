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
from hashlib import file_digest, sha256
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


def _payload_sha256(payload: object) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    if array.dtype.hasobject:
        raise ValueError("Object arrays cannot identify numeric fit input bytes")
    digest = sha256()
    digest.update(
        json.dumps(
            {"dtype": array.dtype.str, "shape": list(array.shape)}, sort_keys=True
        ).encode()
    )
    digest.update(b"\0")
    digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _completion_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.name}.receipt.json")


def _save_new_bundle(bundle: dict, output_path: Path) -> dict:
    """Publish complete files without replacement; roll back our receipt on failure."""
    completion_path = _completion_path(output_path)
    if any(
        path.exists() or path.is_symlink() for path in (output_path, completion_path)
    ):
        raise FileExistsError(
            f"Refusing to replace existing model or receipt: {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_paths: list[Path] = []
    temporary_model: Path | None = None
    temporary_receipt: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent, suffix=".joblib", delete=False
        ) as stream:
            temporary_model = Path(stream.name)
            temporary_paths.append(temporary_model)
            joblib.dump(bundle, stream)
            stream.flush()
            os.fsync(stream.fileno())
        with temporary_model.open("rb") as stream:
            model_sha256 = file_digest(stream, "sha256").hexdigest()
        core = bundle.get("training_receipt", {})
        completion = {
            "format_version": "completed-training-receipt-v1",
            "status": "completed",
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "model": {
                "filename": output_path.name,
                "sha256": model_sha256,
                "byte_size": temporary_model.stat().st_size,
            },
            "training_receipt_core_sha256": _payload_sha256(core),
            "training_receipt": core,
            "model_promoted": False,
            "target_accuracy_verified": False,
        }
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent, suffix=".json", delete=False
        ) as stream:
            temporary_receipt = Path(stream.name)
            temporary_paths.append(temporary_receipt)
            stream.write(json.dumps(completion, sort_keys=True, indent=2).encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_receipt, completion_path)
        os.link(temporary_model, output_path)
        return completion
    except BaseException:
        for published, temporary in (
            (output_path, temporary_model),
            (completion_path, temporary_receipt),
        ):
            if temporary is not None and (published.exists() or published.is_symlink()):
                actual, owned = published.lstat(), temporary.stat()
                if (actual.st_dev, actual.st_ino) == (owned.st_dev, owned.st_ino):
                    published.unlink()
        raise
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)


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
    if any(
        path.exists() or path.is_symlink()
        for path in (output_path, _completion_path(output_path))
    ):
        raise FileExistsError(
            f"Refusing to replace existing model or receipt: {output_path}"
        )

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
    declared_train_entries = {
        (race["race_id"], horse["chulNo"])
        for race in races
        if race["race_date"] <= str(config["split"]["train_end"])
        for horse in race["horses"]
    }
    races, answers, dataset_normalization = _normalize_dataset_before_split(
        races, answers
    )
    rows = _build_feature_rows(races, answers)
    rows, row_normalization = _normalize_feature_rows_before_split(rows)
    if (
        any(
            dataset_normalization[key]
            for key in (
                "duplicate_race_count",
                "duplicate_horse_group_count",
                "dropped_horse_without_chul_count",
            )
        )
        or row_normalization["duplicate_row_count"]
    ):
        raise ValueError("Training normalization silently removed or merged entries")
    actual_entries = {(row["race_id"], row["chulNo"]) for row in rows}
    if actual_entries != expected_entries or len(rows) != len(expected_entries):
        raise ValueError(
            "Training feature construction changed the complete runner field"
        )
    X, y, groups, dates, chuls = _build_arrays(rows, features)

    train_end = str(config["split"]["train_end"])
    train_mask = dates <= train_end
    if not train_mask.any():
        raise SystemExit(f"Empty training mask for train_end={train_end}")

    fit_row_index = [
        [str(groups[index]), int(chuls[index])] for index in np.flatnonzero(train_mask)
    ]
    if {tuple(item) for item in fit_row_index} != declared_train_entries or len(
        fit_row_index
    ) != len(declared_train_entries):
        raise ValueError("Actual fit cohort differs from declared training entries")
    X_train = np.ascontiguousarray(X[train_mask])
    y_train = np.ascontiguousarray(y[train_mask])
    sample_weight = np.where(y_train == 1, model_parameters.positive_class_weight, 1.0)
    for array in (X_train, y_train, sample_weight):
        array.flags.writeable = False
    training_receipt = inputs.receipt()
    training_receipt["fit_inputs"] = {
        "declared_dataset_race_ids": sorted({race["race_id"] for race in races}),
        "declared_train_race_ids": sorted(
            {entry[0] for entry in declared_train_entries}
        ),
        "actual_fit_race_ids": sorted({entry[0] for entry in fit_row_index}),
        "row_index": fit_row_index,
        "row_index_sha256": _payload_sha256(fit_row_index),
        "feature_names": features,
        "feature_order_sha256": _payload_sha256(features),
        "X_sha256": _array_sha256(X_train),
        "y_sha256": _array_sha256(y_train),
        "sample_weight_sha256": _array_sha256(sample_weight),
        "n_rows": len(fit_row_index),
        "train_end": train_end,
        "dataset_normalization": dataset_normalization,
        "row_normalization": row_normalization,
        "model_random_state": model_parameters.random_state,
    }

    inputs.require_unchanged_implementation()
    model = _make_model(model_parameters)
    model.fit(X_train, y_train, clf__sample_weight=sample_weight)

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
        "training_receipt": training_receipt,
        "model_promoted": False,
    }
    inputs.require_unchanged_implementation()
    completion = _save_new_bundle(bundle, output_path)
    summary = {k: v for k, v in bundle.items() if k != "pipeline"}
    print(json.dumps(summary, indent=2, default=str))
    print(f"Saved: {output_path}")
    print(
        f"Completion receipt: {_completion_path(output_path)}; model SHA-256: {completion['model']['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
