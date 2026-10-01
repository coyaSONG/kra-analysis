"""Select and freeze a simple ranker on the lossless Laya candidate surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from xgboost import XGBRanker

FORMAT_VERSION = "single-combo-laya-feature-ranker-v1"
QUESTION_ID = "top3_combo"
NONE_OPTION = "NONE"
DEFAULT_TRAIN = Path(".cache/autoresearch/laya_temporal_dataset/train.jsonl")
DEFAULT_VALIDATION = Path(".cache/autoresearch/laya_temporal_dataset/validation.jsonl")
DEFAULT_TEST = Path(".cache/autoresearch/laya_temporal_dataset/test.jsonl")
DEFAULT_OUTPUT_DIR = Path(".cache/autoresearch/laya_feature_ranker")
FEATURE_NAMES = (
    "is_none",
    "is_default",
    "default_overlap",
    "source_score",
    "ensemble_score",
    "model_rank",
    "member_mean",
    "probability",
    "option_count",
    "field_size",
)
MODEL_SPECS = tuple(
    {
        "name": f"xgb_pairwise_d{depth}_e{estimators}",
        "max_depth": depth,
        "n_estimators": estimators,
    }
    for depth in (2, 3, 4)
    for estimators in (50, 100, 200)
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            rows.append(value)
    if not rows:
        raise ValueError(f"{path} contains no examples")
    return rows


def parse_candidate_description(
    description: str,
    *,
    option_count: int,
    field_size: int,
) -> list[float]:
    if description == NONE_OPTION:
        candidate = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    else:
        horses, separator, raw_features = description.partition("|")
        if not separator or len(horses.split(",")) != 3:
            raise ValueError(f"invalid candidate description: {description!r}")
        values = [float(value) for value in raw_features.split(",")]
        if len(values) != 7:
            raise ValueError(
                f"candidate vector must contain seven values: {description!r}"
            )
        candidate = [
            0.0,
            values[0],
            values[1],
            values[2] / 1000.0,
            values[3] / 1000.0,
            values[4],
            values[5] / 1000.0,
            values[6] / 1000.0,
        ]
    return [*candidate, float(option_count), float(field_size)]


def build_examples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        state = row.get("state")
        questions = row.get("questions")
        expected = row.get("expected")
        if not isinstance(state, dict) or not state.get("race_id"):
            raise ValueError("each row must contain state.race_id")
        race_id = str(state["race_id"])
        if race_id in seen:
            raise ValueError(f"duplicate race_id: {race_id}")
        seen.add(race_id)
        question = questions.get(QUESTION_ID) if isinstance(questions, dict) else None
        expected_label = (
            expected.get(QUESTION_ID) if isinstance(expected, dict) else None
        )
        criteria = question.get("criteria") if isinstance(question, dict) else None
        field_size = state.get("field_size")
        if (
            not isinstance(criteria, dict)
            or not isinstance(expected_label, str)
            or expected_label not in criteria
            or not isinstance(field_size, int)
        ):
            raise ValueError(f"invalid choice example for race {race_id}")
        labels = list(criteria)
        descriptions = [str(criteria[label]) for label in labels]
        examples.append(
            {
                "race_id": race_id,
                "labels": labels,
                "descriptions": descriptions,
                "features": [
                    parse_candidate_description(
                        description,
                        option_count=len(criteria),
                        field_size=field_size,
                    )
                    for description in descriptions
                ],
                "expected_index": labels.index(expected_label),
            }
        )
    return examples


def _flatten(
    examples: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features = np.asarray(
        [feature for example in examples for feature in example["features"]],
        dtype=np.float32,
    )
    labels = np.asarray(
        [
            int(index == example["expected_index"])
            for example in examples
            for index in range(len(example["features"]))
        ],
        dtype=np.float32,
    )
    qid = np.concatenate(
        [
            np.full(len(example["features"]), index, dtype=np.int32)
            for index, example in enumerate(examples)
        ]
    )
    return features, labels, qid


def _model(spec: dict[str, Any]) -> XGBRanker:
    return XGBRanker(
        objective="rank:pairwise",
        n_estimators=int(spec["n_estimators"]),
        max_depth=int(spec["max_depth"]),
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=3.0,
        random_state=42,
        n_jobs=4,
    )


def _fit(spec: dict[str, Any], examples: list[dict[str, Any]]) -> XGBRanker:
    features, labels, qid = _flatten(examples)
    return _model(spec).fit(features, labels, qid=qid, verbose=False)


def score_predictions(
    examples: list[dict[str, Any]], scores: np.ndarray
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    offset = 0
    correct_count = 0
    candidate_correct = 0
    candidate_count = 0
    none_correct = 0
    none_count = 0
    predicted_none_count = 0
    predictions: list[dict[str, Any]] = []
    for example in examples:
        option_count = len(example["features"])
        race_scores = scores[offset : offset + option_count]
        offset += option_count
        predicted_index = int(np.argmax(race_scores))
        expected_index = int(example["expected_index"])
        correct = predicted_index == expected_index
        correct_count += int(correct)
        expected_none = example["descriptions"][expected_index] == NONE_OPTION
        predicted_none = example["descriptions"][predicted_index] == NONE_OPTION
        predicted_none_count += int(predicted_none)
        if expected_none:
            none_count += 1
            none_correct += int(correct)
        else:
            candidate_count += 1
            candidate_correct += int(correct)
        order = np.argsort(race_scores)[::-1]
        margin = (
            float(race_scores[order[0]] - race_scores[order[1]])
            if option_count >= 2
            else None
        )
        predictions.append(
            {
                "race_id": example["race_id"],
                "expected_label": example["labels"][expected_index],
                "expected_description": example["descriptions"][expected_index],
                "predicted_label": example["labels"][predicted_index],
                "predicted_description": example["descriptions"][predicted_index],
                "correct": correct,
                "score_margin": margin,
            }
        )
    if offset != len(scores):
        raise ValueError("score count does not match the candidate rows")
    metrics = {
        "race_count": len(examples),
        "correct_count": correct_count,
        "exact_accuracy": correct_count / len(examples),
        "candidate_target_count": candidate_count,
        "candidate_target_accuracy": (
            candidate_correct / candidate_count if candidate_count else None
        ),
        "none_target_count": none_count,
        "none_target_accuracy": none_correct / none_count if none_count else None,
        "predicted_none_count": predicted_none_count,
    }
    return metrics, predictions


def _evaluate_model(
    model: XGBRanker, examples: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    features, _labels, _qid = _flatten(examples)
    return score_predictions(examples, model.predict(features))


def _heuristic_metrics(
    examples: list[dict[str, Any]], feature_name: str
) -> dict[str, Any]:
    feature_index = FEATURE_NAMES.index(feature_name)
    scores = np.asarray(
        [
            feature[feature_index]
            for example in examples
            for feature in example["features"]
        ],
        dtype=np.float32,
    )
    metrics, _predictions = score_predictions(examples, scores)
    return metrics


def _write_predictions(path: Path, predictions: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for prediction in predictions:
            handle.write(
                json.dumps(prediction, ensure_ascii=False, separators=(",", ":")) + "\n"
            )


def select_and_freeze(
    *,
    train_path: Path,
    validation_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    train_examples = build_examples(_load_jsonl(train_path))
    validation_examples = build_examples(_load_jsonl(validation_path))
    overlap = sorted(
        {example["race_id"] for example in train_examples}
        & {example["race_id"] for example in validation_examples}
    )
    if overlap:
        raise ValueError(f"train/validation overlap: {overlap[:5]}")
    results: list[dict[str, Any]] = []
    validation_predictions_by_name: dict[str, list[dict[str, Any]]] = {}
    for spec in MODEL_SPECS:
        model = _fit(spec, train_examples)
        train_metrics, _train_predictions = _evaluate_model(model, train_examples)
        validation_metrics, validation_predictions = _evaluate_model(
            model, validation_examples
        )
        results.append(
            {
                "spec": spec,
                "train": train_metrics,
                "validation": validation_metrics,
            }
        )
        validation_predictions_by_name[str(spec["name"])] = validation_predictions
    selected = max(
        results,
        key=lambda result: (
            result["validation"]["exact_accuracy"],
            -int(result["spec"]["max_depth"]),
            -int(result["spec"]["n_estimators"]),
        ),
    )
    default_metrics = _heuristic_metrics(validation_examples, "is_default")
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_predictions(
        output_dir / "validation_predictions.jsonl",
        validation_predictions_by_name[str(selected["spec"]["name"])],
    )

    frozen_examples = [*train_examples, *validation_examples]
    frozen_model = _fit(selected["spec"], frozen_examples)
    model_path = output_dir / "frozen_model.json"
    frozen_model.save_model(model_path)
    manifest = {
        "format_version": FORMAT_VERSION,
        "status": "passed",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "feature_names": list(FEATURE_NAMES),
        "train_path": str(train_path),
        "train_sha256": _sha256_file(train_path),
        "train_race_count": len(train_examples),
        "validation_path": str(validation_path),
        "validation_sha256": _sha256_file(validation_path),
        "validation_race_count": len(validation_examples),
        "validation_default_heuristic": default_metrics,
        "model_results": results,
        "selected_spec": selected["spec"],
        "selected_validation": selected["validation"],
        "frozen_fit_race_count": len(frozen_examples),
        "frozen_model_path": str(model_path),
        "frozen_model_sha256": _sha256_file(model_path),
        "final_test_inference_run": False,
        "final_test_labels_used_for_selection": False,
        "recommended_next_action": "evaluate_frozen_model_once_on_sealed_test",
    }
    _write_json(output_dir / "selection_manifest.json", manifest)
    return manifest


def evaluate_frozen_test(
    *,
    test_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    selection_path = output_dir / "selection_manifest.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("feature_names") != list(FEATURE_NAMES):
        raise ValueError("frozen model feature contract does not match this script")
    model_path = Path(selection["frozen_model_path"])
    if _sha256_file(model_path) != selection.get("frozen_model_sha256"):
        raise ValueError("frozen model hash does not match the selection manifest")
    model = XGBRanker()
    model.load_model(model_path)
    test_examples = build_examples(_load_jsonl(test_path))
    fit_race_ids = {
        example["race_id"]
        for path in (Path(selection["train_path"]), Path(selection["validation_path"]))
        for example in build_examples(_load_jsonl(path))
    }
    overlap = sorted(fit_race_ids & {example["race_id"] for example in test_examples})
    if overlap:
        raise ValueError(f"frozen fit/test overlap: {overlap[:5]}")
    metrics, predictions = _evaluate_model(model, test_examples)
    _write_predictions(output_dir / "test_predictions.jsonl", predictions)
    report = {
        "format_version": FORMAT_VERSION,
        "status": "passed",
        "counts_as_70_percent_evidence": False,
        "selection_manifest_sha256": _sha256_file(selection_path),
        "frozen_model_sha256": _sha256_file(model_path),
        "selected_spec": selection["selected_spec"],
        "selected_validation": selection["selected_validation"],
        "test_path": str(test_path),
        "test_sha256": _sha256_file(test_path),
        "test": metrics,
        "final_test_inference_run": True,
        "final_test_labels_used_for_selection": False,
        "goal_met_on_test": metrics["exact_accuracy"] >= 0.70,
        "recommended_next_action": "compare_with_strict_existing_selector",
    }
    _write_json(output_dir / "test_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--evaluate-test", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    if args.evaluate_test:
        result = evaluate_frozen_test(test_path=args.test, output_dir=args.output_dir)
    else:
        result = select_and_freeze(
            train_path=args.train,
            validation_path=args.validation,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return int(args.require_pass and result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
