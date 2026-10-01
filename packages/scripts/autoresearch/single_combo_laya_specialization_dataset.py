"""Build deterministic option-order augmentation for Laya specialization."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch.clean_sparse_multichoice_policy_selector_probe import (  # noqa: E402
    DEFAULT_CACHE_DIR,
)
from autoresearch.single_combo_laya_temporal_dataset_export import (  # noqa: E402
    OPTION_LABELS,
    QUESTION_ID,
)

FORMAT_VERSION = "single-combo-laya-specialization-dataset-v1"
DEFAULT_SOURCE = DEFAULT_CACHE_DIR / "laya_temporal_dataset" / "train.jsonl"
DEFAULT_OUTPUT = DEFAULT_CACHE_DIR / "laya_specialization" / "train_augmented.jsonl"
DEFAULT_MANIFEST = DEFAULT_CACHE_DIR / "laya_specialization" / "manifest.json"
DEFAULT_AUGMENTATIONS = 8
DEFAULT_LABEL_SMOOTHING = 0.05
DEFAULT_SEED = "kra-laya-specialization-v1"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path} contains no examples")
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            )


def _permutation_key(
    *,
    seed: str,
    race_id: str,
    augmentation_index: int,
    description: str,
) -> str:
    payload = f"{seed}|{race_id}|{augmentation_index}|{description}".encode()
    return _sha256_bytes(payload)


def _smoothed_probabilities(
    labels: list[str],
    expected_label: str,
    smoothing: float,
) -> dict[str, float]:
    if expected_label not in labels:
        raise ValueError("expected label is not present in the augmented criteria")
    if not 0.0 <= smoothing < 1.0:
        raise ValueError("label smoothing must be in [0, 1)")
    if len(labels) < 2:
        raise ValueError("choice training rows require at least two labels")
    other_probability = smoothing / (len(labels) - 1)
    return {
        label: (1.0 - smoothing if label == expected_label else other_probability)
        for label in labels
    }


def augment_example(
    row: dict[str, Any],
    *,
    augmentation_index: int,
    label_smoothing: float,
    seed: str,
) -> dict[str, Any]:
    state = row.get("state")
    if not isinstance(state, dict):
        raise ValueError("training state must be a dictionary")
    race_id = str(state.get("race_id") or "")
    if not race_id:
        raise ValueError("training state must contain race_id")
    questions = row.get("questions")
    expected = row.get("expected")
    if not isinstance(questions, dict) or not isinstance(expected, dict):
        raise ValueError(
            "training row must contain questions and expected dictionaries"
        )
    question = questions.get(QUESTION_ID)
    expected_label = expected.get(QUESTION_ID)
    if not isinstance(question, dict) or not isinstance(expected_label, str):
        raise ValueError(f"training row is missing {QUESTION_ID}")
    criteria = question.get("criteria")
    if not isinstance(criteria, dict) or len(criteria) < 2:
        raise ValueError("choice criteria must contain at least two options")
    if expected_label not in criteria:
        raise ValueError("expected label is missing from source criteria")

    expected_description = str(criteria[expected_label])
    descriptions = [str(description) for description in criteria.values()]
    if len(set(descriptions)) != len(descriptions):
        raise ValueError("criteria descriptions must be unique")
    descriptions.sort(
        key=lambda description: _permutation_key(
            seed=seed,
            race_id=race_id,
            augmentation_index=augmentation_index,
            description=description,
        )
    )
    if len(descriptions) > len(OPTION_LABELS):
        raise ValueError("choice criteria exceed the supported option labels")
    augmented_criteria = {
        OPTION_LABELS[index]: description
        for index, description in enumerate(descriptions)
    }
    augmented_expected = next(
        label
        for label, description in augmented_criteria.items()
        if description == expected_description
    )
    labels = list(augmented_criteria)
    probabilities = _smoothed_probabilities(
        labels,
        augmented_expected,
        label_smoothing,
    )
    return {
        "state": state,
        "questions": {
            QUESTION_ID: {
                "type": "choice",
                "instructions": str(question.get("instructions") or ""),
                "criteria": augmented_criteria,
            }
        },
        "expected": {QUESTION_ID: augmented_expected},
        "gold": {
            QUESTION_ID: {
                "label": augmented_expected,
                "probabilities": probabilities,
            }
        },
        "tags": [
            "split:train",
            "augmentation:option_order",
            f"augmentation_index:{augmentation_index}",
        ],
        "language": "en",
        "metadata": {
            "source_race_id": race_id,
            "augmentation_index": augmentation_index,
            "independent_example_weight": round(1.0, 8),
        },
    }


def build_specialization_dataset(
    source_rows: list[dict[str, Any]],
    *,
    augmentations_per_race: int = DEFAULT_AUGMENTATIONS,
    label_smoothing: float = DEFAULT_LABEL_SMOOTHING,
    seed: str = DEFAULT_SEED,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if augmentations_per_race < 1:
        raise ValueError("augmentations_per_race must be positive")
    race_ids = [str(row.get("state", {}).get("race_id") or "") for row in source_rows]
    if any(not race_id for race_id in race_ids):
        raise ValueError("every source row must contain a race_id")
    if len(set(race_ids)) != len(race_ids):
        raise ValueError("source rows must contain one example per independent race")

    output_rows: list[dict[str, Any]] = []
    expected_labels: list[str] = []
    permutation_digests_by_race: dict[str, set[str]] = {
        race_id: set() for race_id in race_ids
    }
    for source_row in source_rows:
        race_id = str(source_row["state"]["race_id"])
        for augmentation_index in range(augmentations_per_race):
            row = augment_example(
                source_row,
                augmentation_index=augmentation_index,
                label_smoothing=label_smoothing,
                seed=seed,
            )
            output_rows.append(row)
            expected_labels.append(row["expected"][QUESTION_ID])
            criteria = row["questions"][QUESTION_ID]["criteria"]
            permutation_digests_by_race[race_id].add(
                _sha256_bytes(
                    json.dumps(
                        criteria,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode()
                )
            )

    distinct_permutations = [
        len(permutation_digests_by_race[race_id]) for race_id in race_ids
    ]
    manifest = {
        "format_version": FORMAT_VERSION,
        "status": "passed"
        if output_rows
        and min(distinct_permutations, default=0) == augmentations_per_race
        else "failed",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "seed": seed,
        "independent_race_count": len(source_rows),
        "augmentations_per_race": augmentations_per_race,
        "training_row_count": len(output_rows),
        "label_smoothing": label_smoothing,
        "expected_label_distribution": dict(sorted(Counter(expected_labels).items())),
        "distinct_permutations_per_race_min": min(distinct_permutations, default=None),
        "distinct_permutations_per_race_max": max(distinct_permutations, default=None),
        "independent_sample_accounting": (
            "option-order variants share one race outcome and count as one independent race"
        ),
        "recommended_next_action": "run_train_only_laya_specialization",
    }
    return output_rows, manifest


def export_specialization_dataset(
    *,
    source_path: Path = DEFAULT_SOURCE,
    output_path: Path = DEFAULT_OUTPUT,
    manifest_path: Path = DEFAULT_MANIFEST,
    augmentations_per_race: int = DEFAULT_AUGMENTATIONS,
    label_smoothing: float = DEFAULT_LABEL_SMOOTHING,
    seed: str = DEFAULT_SEED,
) -> dict[str, Any]:
    source_rows = _load_jsonl(source_path)
    rows, manifest = build_specialization_dataset(
        source_rows,
        augmentations_per_race=augmentations_per_race,
        label_smoothing=label_smoothing,
        seed=seed,
    )
    _write_jsonl(output_path, rows)
    manifest.update(
        {
            "source_path": str(source_path),
            "source_sha256": _sha256_file(source_path),
            "output_path": str(output_path),
            "output_sha256": _sha256_file(output_path),
        }
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--augmentations-per-race", type=int, default=DEFAULT_AUGMENTATIONS
    )
    parser.add_argument(
        "--label-smoothing", type=float, default=DEFAULT_LABEL_SMOOTHING
    )
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    manifest = export_specialization_dataset(
        source_path=args.source,
        output_path=args.output,
        manifest_path=args.manifest,
        augmentations_per_race=args.augmentations_per_race,
        label_smoothing=args.label_smoothing,
        seed=args.seed,
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return int(args.require_pass and manifest["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
