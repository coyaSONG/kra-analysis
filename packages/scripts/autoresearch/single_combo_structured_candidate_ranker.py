"""Rank top-three candidates with structured race and runner features."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from xgboost import XGBRanker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autoresearch import single_combo_laya_feature_ranker as base_ranker  # noqa: E402

FORMAT_VERSION = "single-combo-structured-candidate-ranker-v1"
DEFAULT_TRAIN = Path(
    ".cache/autoresearch/laya_oof_training_dataset/train.jsonl"
)
DEFAULT_VALIDATION = Path(
    ".cache/autoresearch/laya_oof_training_dataset/validation.jsonl"
)
DEFAULT_OUTPUT_DIR = Path(
    ".cache/autoresearch/structured_candidate_ranker"
)
QUESTION_ID = base_ranker.QUESTION_ID
NONE_OPTION = base_ranker.NONE_OPTION
RUNNER_FIELDS = (
    "age",
    "sex",
    "rating",
    "carried_x10",
    "weight_delta",
    "horse_place_x10",
    "recent_top3_x1000",
    "jockey_top3_x1000",
    "trainer_top3_x1000",
    "rest",
)
RACE_FIELDS = (
    "meet",
    "race_no",
    "distance",
    "field_size",
    "class",
    "weather",
    "track_pct",
    "wet",
    "handicap",
)
RUNNER_AGGREGATES = (
    "mean",
    "min",
    "max",
    "range",
    "missing_count",
    "mean_delta_field",
    "mean_percentile",
)
BASE_FEATURE_NAMES = tuple(base_ranker.FEATURE_NAMES)
STRUCTURED_FEATURE_NAMES = (
    *BASE_FEATURE_NAMES,
    *(f"race_{field}" for field in RACE_FIELDS),
    "horse_number_mean",
    "horse_number_min",
    "horse_number_max",
    "horse_number_range",
    *(
        f"{field}_{aggregate}"
        for field in RUNNER_FIELDS
        for aggregate in RUNNER_AGGREGATES
    ),
)
FEATURE_FAMILIES = {
    "base": len(BASE_FEATURE_NAMES),
    "structured": len(STRUCTURED_FEATURE_NAMES),
}
MODEL_SPECS = tuple(
    {
        "name": f"xgb_pairwise_d{depth}_e{estimators}",
        "max_depth": depth,
        "n_estimators": estimators,
    }
    for depth in (2, 3, 4)
    for estimators in (100, 300)
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


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return math.nan
    result = float(value)
    return result if math.isfinite(result) else math.nan


def _candidate_horses(description: str) -> tuple[int, int, int] | None:
    if description == NONE_OPTION:
        return None
    horses, separator, _features = description.partition("|")
    if not separator:
        raise ValueError(f"invalid candidate description: {description!r}")
    values = tuple(int(value) for value in horses.split(","))
    if len(values) != 3 or len(set(values)) != 3:
        raise ValueError(f"candidate must contain three distinct horses: {description!r}")
    return tuple(sorted(values))  # type: ignore[return-value]


def _runner_table(state: dict[str, Any]) -> dict[int, dict[str, float]]:
    fields = state.get("runner_fields")
    rows = state.get("runner_values")
    expected_fields = ("number", *RUNNER_FIELDS)
    if fields != list(expected_fields) or not isinstance(rows, list):
        raise ValueError("runner state does not match the v5 field contract")
    table: dict[int, dict[str, float]] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) != len(expected_fields):
            raise ValueError("runner row does not match runner_fields")
        number = int(row[0])
        if number in table:
            raise ValueError(f"duplicate runner number {number}")
        table[number] = {
            field: _number(value)
            for field, value in zip(RUNNER_FIELDS, row[1:], strict=True)
        }
    return table


def _finite(values: list[float]) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    return array[np.isfinite(array)]


def structured_candidate_features(
    description: str,
    *,
    state: dict[str, Any],
    option_count: int,
) -> list[float]:
    horses = _candidate_horses(description)
    if horses is None:
        raise ValueError("NONE is not a rankable top-three candidate")
    field_size = state.get("field_size")
    if not isinstance(field_size, int):
        raise ValueError("state.field_size must be an integer")
    base = base_ranker.parse_candidate_description(
        description,
        option_count=option_count,
        field_size=field_size,
    )
    table = _runner_table(state)
    missing_horses = sorted(set(horses) - set(table))
    if missing_horses:
        raise ValueError(f"candidate references missing horses: {missing_horses}")
    features = [*base, *(_number(state.get(field)) for field in RACE_FIELDS)]
    horse_numbers = np.asarray(horses, dtype=np.float64)
    features.extend(
        [
            float(horse_numbers.mean()),
            float(horse_numbers.min()),
            float(horse_numbers.max()),
            float(horse_numbers.max() - horse_numbers.min()),
        ]
    )
    for field in RUNNER_FIELDS:
        candidate_values = [table[horse][field] for horse in horses]
        candidate_finite = _finite(candidate_values)
        field_finite = _finite([runner[field] for runner in table.values()])
        missing_count = 3 - len(candidate_finite)
        if len(candidate_finite):
            candidate_mean = float(candidate_finite.mean())
            candidate_min = float(candidate_finite.min())
            candidate_max = float(candidate_finite.max())
            candidate_range = candidate_max - candidate_min
        else:
            candidate_mean = candidate_min = candidate_max = candidate_range = math.nan
        field_mean = float(field_finite.mean()) if len(field_finite) else math.nan
        percentiles = [
            float(np.mean(field_finite <= value))
            for value in candidate_finite
            if len(field_finite)
        ]
        features.extend(
            [
                candidate_mean,
                candidate_min,
                candidate_max,
                candidate_range,
                float(missing_count),
                candidate_mean - field_mean,
                float(np.mean(percentiles)) if percentiles else math.nan,
            ]
        )
    if len(features) != len(STRUCTURED_FEATURE_NAMES):
        raise AssertionError("structured feature width does not match its contract")
    return features


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
        criteria = question.get("criteria") if isinstance(question, dict) else None
        expected_label = (
            expected.get(QUESTION_ID) if isinstance(expected, dict) else None
        )
        if (
            not isinstance(criteria, dict)
            or not isinstance(expected_label, str)
            or expected_label not in criteria
        ):
            raise ValueError(f"invalid choice example for race {race_id}")
        candidate_items = [
            (label, str(description))
            for label, description in criteria.items()
            if str(description) != NONE_OPTION
        ]
        labels = [label for label, _description in candidate_items]
        descriptions = [description for _label, description in candidate_items]
        expected_description = str(criteria[expected_label])
        expected_index = (
            labels.index(expected_label) if expected_description != NONE_OPTION else None
        )
        examples.append(
            {
                "race_id": race_id,
                "race_date": race_id[:8],
                "labels": labels,
                "descriptions": descriptions,
                "features": [
                    structured_candidate_features(
                        description,
                        state=state,
                        option_count=len(candidate_items),
                    )
                    for description in descriptions
                ],
                "expected_index": expected_index,
            }
        )
    return examples


def temporal_inner_split(
    examples: list[dict[str, Any]], validation_date_fraction: float = 0.2
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    if not 0.0 < validation_date_fraction < 1.0:
        raise ValueError("validation_date_fraction must be between zero and one")
    dates = sorted({str(example["race_date"]) for example in examples})
    if len(dates) < 2:
        raise ValueError("temporal split requires at least two race dates")
    validation_date_count = max(1, math.ceil(len(dates) * validation_date_fraction))
    validation_dates = set(dates[-validation_date_count:])
    train = [
        example for example in examples if example["race_date"] not in validation_dates
    ]
    validation = [
        example for example in examples if example["race_date"] in validation_dates
    ]
    if not train or not validation:
        raise ValueError("temporal split produced an empty partition")
    cutoff = min(validation_dates)
    return train, validation, cutoff


def _flatten_training(
    examples: list[dict[str, Any]], feature_count: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    eligible = [example for example in examples if example["expected_index"] is not None]
    if not eligible:
        raise ValueError("training split has no rankable target races")
    features = np.asarray(
        [
            feature[:feature_count]
            for example in eligible
            for feature in example["features"]
        ],
        dtype=np.float32,
    )
    labels = np.asarray(
        [
            int(index == example["expected_index"])
            for example in eligible
            for index in range(len(example["features"]))
        ],
        dtype=np.float32,
    )
    qid = np.concatenate(
        [
            np.full(len(example["features"]), index, dtype=np.int32)
            for index, example in enumerate(eligible)
        ]
    )
    return features, labels, qid


def _prediction_features(
    examples: list[dict[str, Any]], feature_count: int
) -> np.ndarray:
    return np.asarray(
        [
            feature[:feature_count]
            for example in examples
            for feature in example["features"]
        ],
        dtype=np.float32,
    )


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


def _fit(
    spec: dict[str, Any], examples: list[dict[str, Any]], feature_count: int
) -> XGBRanker:
    features, labels, qid = _flatten_training(examples, feature_count)
    return _model(spec).fit(features, labels, qid=qid, verbose=False)


def score_predictions(
    examples: list[dict[str, Any]], scores: np.ndarray
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    offset = 0
    correct_count = 0
    candidate_target_count = 0
    predictions: list[dict[str, Any]] = []
    for example in examples:
        option_count = len(example["features"])
        race_scores = scores[offset : offset + option_count]
        offset += option_count
        predicted_index = int(np.argmax(race_scores))
        expected_index = example["expected_index"]
        correct = expected_index is not None and predicted_index == expected_index
        correct_count += int(correct)
        candidate_target_count += int(expected_index is not None)
        predictions.append(
            {
                "race_id": example["race_id"],
                "expected_description": (
                    example["descriptions"][expected_index]
                    if expected_index is not None
                    else NONE_OPTION
                ),
                "predicted_description": example["descriptions"][predicted_index],
                "top3_correct": correct,
            }
        )
    if offset != len(scores):
        raise ValueError("score count does not match candidate rows")
    race_count = len(examples)
    return (
        {
            "race_count": race_count,
            "top3_correct_count": correct_count,
            "top3_exact_accuracy": correct_count / race_count,
            "candidate_target_count": candidate_target_count,
            "candidate_oracle_exact_accuracy": candidate_target_count / race_count,
            "candidate_target_accuracy": (
                correct_count / candidate_target_count
                if candidate_target_count
                else None
            ),
        },
        predictions,
    )


def _evaluate(
    model: XGBRanker,
    examples: list[dict[str, Any]],
    feature_count: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return score_predictions(examples, model.predict(_prediction_features(examples, feature_count)))


def _default_metrics(examples: list[dict[str, Any]]) -> dict[str, Any]:
    default_index = BASE_FEATURE_NAMES.index("is_default")
    scores = np.asarray(
        [
            feature[default_index]
            for example in examples
            for feature in example["features"]
        ],
        dtype=np.float32,
    )
    return score_predictions(examples, scores)[0]


def run(args: argparse.Namespace) -> dict[str, Any]:
    train_examples = build_examples(base_ranker._load_jsonl(args.train))  # noqa: SLF001
    validation_examples = build_examples(
        base_ranker._load_jsonl(args.validation)  # noqa: SLF001
    )
    overlap = sorted(
        {example["race_id"] for example in train_examples}
        & {example["race_id"] for example in validation_examples}
    )
    if overlap:
        raise ValueError(f"train/validation overlap: {overlap[:5]}")
    inner_train, inner_validation, inner_cutoff = temporal_inner_split(
        train_examples,
        args.inner_validation_date_fraction,
    )
    results: list[dict[str, Any]] = []
    for family, feature_count in FEATURE_FAMILIES.items():
        for spec in MODEL_SPECS:
            model = _fit(spec, inner_train, feature_count)
            metrics, _predictions = _evaluate(
                model,
                inner_validation,
                feature_count,
            )
            results.append(
                {"family": family, "feature_count": feature_count, "spec": spec, "inner_validation": metrics}
            )
    selected = max(
        results,
        key=lambda result: (
            result["inner_validation"]["top3_exact_accuracy"],
            result["family"] == "base",
            -int(result["spec"]["max_depth"]),
            -int(result["spec"]["n_estimators"]),
        ),
    )
    family_best = {
        family: max(
            (result for result in results if result["family"] == family),
            key=lambda result: (
                result["inner_validation"]["top3_exact_accuracy"],
                -int(result["spec"]["max_depth"]),
                -int(result["spec"]["n_estimators"]),
            ),
        )
        for family in FEATURE_FAMILIES
    }
    validation_by_family: dict[str, Any] = {}
    selected_model: XGBRanker | None = None
    selected_predictions: list[dict[str, Any]] = []
    for family, best in family_best.items():
        feature_count = int(best["feature_count"])
        model = _fit(best["spec"], train_examples, feature_count)
        metrics, predictions = _evaluate(model, validation_examples, feature_count)
        validation_by_family[family] = {
            "spec": best["spec"],
            "inner_validation": best["inner_validation"],
            "october_validation": metrics,
        }
        if family == selected["family"]:
            selected_model = model
            selected_predictions = predictions
    if selected_model is None:
        raise AssertionError("selected family model was not fitted")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "diagnostic_model.json"
    selected_model.save_model(model_path)
    predictions_path = args.output_dir / "october_predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as handle:
        for prediction in selected_predictions:
            handle.write(
                json.dumps(prediction, ensure_ascii=False, separators=(",", ":"))
                + "\n"
            )
    strict_artifact = json.loads(args.strict_baseline.read_text(encoding="utf-8"))
    strict_baseline = base_ranker.strict_baseline_comparison(
        strict_artifact,
        race_ids={example["race_id"] for example in validation_examples},
        window_name="fold_a",
    )
    selected_validation = validation_by_family[str(selected["family"])][
        "october_validation"
    ]
    report = {
        "format_version": FORMAT_VERSION,
        "status": "passed",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "selection_uses_october_labels": False,
        "october_has_been_used_by_prior_research": True,
        "train_path": str(args.train),
        "train_sha256": _sha256_file(args.train),
        "validation_path": str(args.validation),
        "validation_sha256": _sha256_file(args.validation),
        "train_race_count": len(train_examples),
        "inner_train_race_count": len(inner_train),
        "inner_validation_race_count": len(inner_validation),
        "inner_validation_cutoff": inner_cutoff,
        "validation_race_count": len(validation_examples),
        "feature_names": {
            "base": list(BASE_FEATURE_NAMES),
            "structured": list(STRUCTURED_FEATURE_NAMES),
        },
        "model_results": results,
        "selected": selected,
        "validation_by_family": validation_by_family,
        "validation_default_heuristic": _default_metrics(validation_examples),
        "strict_baseline": strict_baseline,
        "selected_top3_correct_delta_vs_strict": (
            selected_validation["top3_correct_count"]
            - strict_baseline["correct_count"]
        ),
        "diagnostic_model_path": str(model_path),
        "diagnostic_model_sha256": _sha256_file(model_path),
        "predictions_path": str(predictions_path),
        "recommended_next_action": "collect_new_forward_holdout_before_promotion",
    }
    _write_json(args.output_dir / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--strict-baseline",
        type=Path,
        default=base_ranker.DEFAULT_STRICT_BASELINE,
    )
    parser.add_argument("--inner-validation-date-fraction", type=float, default=0.2)
    args = parser.parse_args()
    report = run(args)
    summary = {
        key: report[key]
        for key in (
            "status",
            "train_race_count",
            "inner_train_race_count",
            "inner_validation_race_count",
            "inner_validation_cutoff",
            "selected",
            "validation_by_family",
            "validation_default_heuristic",
            "strict_baseline",
            "selected_top3_correct_delta_vs_strict",
            "recommended_next_action",
        )
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
