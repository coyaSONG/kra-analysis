"""Evaluate a Laya checkpoint with position-balanced option rotations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autoresearch import single_combo_laya_mps_specialize as specialize  # noqa: E402

FORMAT_VERSION = "single-combo-laya-order-rotation-evaluation-v1"
DEFAULT_MODEL_DIR = Path(
    ".cache/autoresearch/laya_oof_specialization/full_encoder_probe"
)
DEFAULT_DATASET = Path(
    ".cache/autoresearch/laya_oof_training_dataset/validation.jsonl"
)
DEFAULT_OUTPUT = Path(
    ".cache/autoresearch/laya_oof_specialization/order_rotation_evaluation.json"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_rotation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rotated_rows: list[dict[str, Any]] = []
    for row in rows:
        question = specialize._question(row)  # noqa: SLF001
        criteria = question.get("criteria")
        if not isinstance(criteria, dict) or len(criteria) < 2:
            raise ValueError("rotation evaluation requires at least two choices")
        labels = list(criteria)
        for rotation_index in range(len(labels)):
            order = labels[rotation_index:] + labels[:rotation_index]
            rotated = copy.deepcopy(row)
            rotated_question = specialize._question(rotated)  # noqa: SLF001
            rotated_question["criteria"] = {
                label: criteria[label] for label in order
            }
            metadata = (
                dict(rotated.get("metadata"))
                if isinstance(rotated.get("metadata"), dict)
                else {}
            )
            metadata.update(
                {
                    "augmentation_index": rotation_index,
                    "rotation_count": len(labels),
                    "rotation_kind": "cyclic_position_balance",
                }
            )
            rotated["metadata"] = metadata
            rotated_rows.append(rotated)
    return rotated_rows


def aggregate_rotation_records(
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_race: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_race[str(record["race_id"])].append(record)
    if not by_race:
        raise ValueError("cannot aggregate an empty record set")

    choice_correct_count = 0
    top3_correct_count = 0
    candidate_target_count = 0
    candidate_correct_count = 0
    none_target_count = 0
    none_correct_count = 0
    predicted_none_count = 0
    stable_race_count = 0
    unique_prediction_total = 0
    predictions: list[dict[str, Any]] = []
    for race_id, race_records in sorted(by_race.items()):
        ordered = sorted(
            race_records,
            key=lambda record: int(record["augmentation_index"]),
        )
        rotation_indices = [int(record["augmentation_index"]) for record in ordered]
        if rotation_indices != list(range(len(ordered))):
            raise ValueError(f"{race_id} rotations must be contiguous from zero")
        reference = ordered[0]
        reference_mapping = dict(
            zip(reference["labels"], reference["descriptions"], strict=True)
        )
        expected_label = str(reference["expected_label"])
        expected_description = str(reference["expected_description"])
        probability_totals = dict.fromkeys(reference["labels"], 0.0)
        variant_predictions: list[str] = []
        for record in ordered:
            mapping = dict(
                zip(record["labels"], record["descriptions"], strict=True)
            )
            if mapping != reference_mapping:
                raise ValueError(f"{race_id} changed label meanings across rotations")
            if (
                record["expected_label"] != expected_label
                or record["expected_description"] != expected_description
            ):
                raise ValueError(f"{race_id} changed targets across rotations")
            probabilities = specialize._softmax(record["logits"], 1.0)  # noqa: SLF001
            for label, probability in zip(
                record["labels"], probabilities, strict=True
            ):
                probability_totals[label] += probability / len(ordered)
            predicted_index = max(
                range(len(probabilities)), key=probabilities.__getitem__
            )
            variant_predictions.append(str(record["labels"][predicted_index]))

        predicted_label = max(
            reference["labels"], key=probability_totals.__getitem__
        )
        predicted_description = reference_mapping[predicted_label]
        choice_correct = predicted_label == expected_label
        top3_correct = choice_correct and expected_description != specialize.NONE_OPTION
        choice_correct_count += int(choice_correct)
        top3_correct_count += int(top3_correct)
        predicted_none_count += int(predicted_description == specialize.NONE_OPTION)
        if expected_description == specialize.NONE_OPTION:
            none_target_count += 1
            none_correct_count += int(choice_correct)
        else:
            candidate_target_count += 1
            candidate_correct_count += int(choice_correct)
        unique_prediction_count = len(set(variant_predictions))
        unique_prediction_total += unique_prediction_count
        stable_race_count += int(unique_prediction_count == 1)
        predictions.append(
            {
                "race_id": race_id,
                "rotation_count": len(ordered),
                "expected_label": expected_label,
                "expected_description": expected_description,
                "predicted_label": predicted_label,
                "predicted_description": predicted_description,
                "choice_correct": choice_correct,
                "top3_correct": top3_correct,
                "unique_variant_prediction_count": unique_prediction_count,
                "mean_probabilities": probability_totals,
            }
        )

    race_count = len(by_race)
    metrics = {
        "race_count": race_count,
        "choice_correct_count": choice_correct_count,
        "choice_accuracy": choice_correct_count / race_count,
        "top3_correct_count": top3_correct_count,
        "top3_exact_accuracy": top3_correct_count / race_count,
        "candidate_target_count": candidate_target_count,
        "candidate_target_accuracy": (
            candidate_correct_count / candidate_target_count
            if candidate_target_count
            else None
        ),
        "none_target_count": none_target_count,
        "none_target_accuracy": (
            none_correct_count / none_target_count if none_target_count else None
        ),
        "predicted_none_count": predicted_none_count,
        "stable_race_count": stable_race_count,
        "stable_race_rate": stable_race_count / race_count,
        "mean_unique_variant_predictions": unique_prediction_total / race_count,
    }
    return metrics, predictions


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    from laya.common import QTYPES, build_model, build_sequence
    from safetensors.torch import load_file
    from transformers import AutoTokenizer

    model_dir = args.model_dir.resolve()
    source_rows = specialize._load_jsonl(args.dataset)  # noqa: SLF001
    rotation_rows = build_rotation_rows(source_rows)
    config = json.loads((model_dir / "rl_agent_config.json").read_text())
    config["max_len"] = args.max_len
    config["head_max_len"] = args.head_max_len
    tokenizer = AutoTokenizer.from_pretrained(model_dir / "tokenizer")
    items = specialize._build_items(  # noqa: SLF001
        rotation_rows,
        tokenizer=tokenizer,
        build_sequence=build_sequence,
        qtypes=QTYPES,
        max_len=args.max_len,
        head_max_len=args.head_max_len,
    )
    model = build_model(config, encoder_dir=model_dir / "encoder")
    model.load_state_dict(load_file(str(model_dir / "model.safetensors")), strict=True)
    model.float()
    device_name = args.device
    if device_name == "auto":
        device_name = "mps" if torch.backends.mps.is_available() else "cpu"
    if device_name == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS was requested but is unavailable")
    device = torch.device(device_name)
    model.to(device)
    records = specialize._evaluate(  # noqa: SLF001
        model,
        items,
        tokenizer=tokenizer,
        torch=torch,
        device=device,
        batch_size=args.batch_size,
    )
    canonical_records = [
        record for record in records if record["augmentation_index"] == 0
    ]
    canonical_metrics = specialize.score_records(canonical_records)
    all_rotation_metrics = specialize.score_records(records)
    ensemble_metrics, predictions = aggregate_rotation_records(records)
    per_rotation = {
        str(rotation_index): specialize.score_records(
            [
                record
                for record in records
                if record["augmentation_index"] == rotation_index
            ]
        )
        for rotation_index in sorted(
            {int(record["augmentation_index"]) for record in records}
        )
    }
    report = {
        "format_version": FORMAT_VERSION,
        "status": "passed",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "model_dir": str(args.model_dir),
        "model_sha256": _sha256_file(model_dir / "model.safetensors"),
        "dataset_path": str(args.dataset),
        "dataset_sha256": _sha256_file(args.dataset),
        "device": str(device),
        "source_race_count": len(source_rows),
        "rotation_row_count": len(rotation_rows),
        "canonical": canonical_metrics,
        "all_rotations": all_rotation_metrics,
        "rotation_ensemble": ensemble_metrics,
        "top3_correct_delta_vs_canonical": (
            ensemble_metrics["top3_correct_count"]
            - canonical_metrics["top3_correct_count"]
        ),
        "per_rotation": per_rotation,
        "predictions": predictions,
        "recommended_next_action": "compare_rotation_ensemble_with_strict_fallback",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", choices=("auto", "mps", "cpu"), default="auto")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-len", type=int, default=1024)
    parser.add_argument("--head-max-len", type=int, default=512)
    args = parser.parse_args()
    if min(args.batch_size, args.max_len, args.head_max_len) < 1:
        raise ValueError("batch and token limits must be positive")
    report = evaluate(args)
    summary = {
        key: report[key]
        for key in (
            "status",
            "source_race_count",
            "rotation_row_count",
            "canonical",
            "rotation_ensemble",
            "top3_correct_delta_vs_canonical",
            "recommended_next_action",
        )
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
