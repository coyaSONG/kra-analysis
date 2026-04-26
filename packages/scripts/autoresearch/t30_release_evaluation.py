"""Evaluate T-30 operational release features on offline snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prediction_input_schema import (
    ALTERNATIVE_RANKING_ALLOWED_FEATURES,
    build_alternative_ranking_rows_for_race,
)
from shared.t30_release_contract import (
    t30_disallowed_overlay_feature_names,
    t30_release_feature_names,
    validate_t30_release_overlay_features,
)
from shared.t30_release_gate import build_t30_release_gate_report

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "clean_model_config.json"
REPORT_VERSION = "t30-release-evaluation-v1"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_baseline_features(config_path: Path) -> tuple[list[str], list[str]]:
    config = _load_json(config_path)
    raw_features = [str(feature) for feature in config.get("features", [])]
    disallowed = set(t30_disallowed_overlay_feature_names())
    removed = [feature for feature in raw_features if feature in disallowed]
    features = [feature for feature in raw_features if feature not in disallowed]
    allowed = set(ALTERNATIVE_RANKING_ALLOWED_FEATURES)
    unknown = sorted(set(features) - allowed)
    if unknown:
        raise ValueError(
            f"baseline config contains non-operational features: {unknown}"
        )
    validate_t30_release_overlay_features(features)
    return features, removed


def _release_features(baseline_features: list[str]) -> list[str]:
    selected = list(
        dict.fromkeys(
            [*baseline_features, *t30_release_feature_names(current_model_only=True)]
        )
    )
    allowed = set(ALTERNATIVE_RANKING_ALLOWED_FEATURES)
    unknown = sorted(set(selected) - allowed)
    if unknown:
        raise ValueError(
            f"release feature set contains non-operational features: {unknown}"
        )
    validate_t30_release_overlay_features(selected)
    return selected


def _build_rows(
    races: list[dict[str, Any]], answers: dict[str, list[int]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for race in races:
        race_id = str(race.get("race_id") or "")
        actual_top3 = answers.get(race_id, [])[:3]
        if len(actual_top3) != 3:
            continue
        rows.extend(
            build_alternative_ranking_rows_for_race(
                race,
                actual_top3=actual_top3,
                validate_rows=True,
            )
        )
    return rows


def _matrix(
    rows: list[dict[str, Any]], features: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x = np.array(
        [[row.get(feature, np.nan) for feature in features] for row in rows],
        dtype=float,
    )
    y = np.array([int(row["target"]) for row in rows], dtype=int)
    groups = np.array([str(row["race_id"]) for row in rows])
    chul_nos = np.array([int(row["chulNo"]) for row in rows], dtype=int)
    return x, y, groups, chul_nos


def _make_model() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    max_depth=None,
                    learning_rate=0.03,
                    max_iter=700,
                    min_samples_leaf=35,
                    l2_regularization=0.4,
                    random_state=42,
                ),
            ),
        ]
    )


def _summarize_predictions(
    *,
    groups: np.ndarray,
    chul_nos: np.ndarray,
    probabilities: np.ndarray,
    answers: dict[str, list[int]],
) -> dict[str, Any]:
    bucket: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for race_id, chul_no, probability in zip(
        groups, chul_nos, probabilities, strict=False
    ):
        bucket[str(race_id)].append((float(probability), int(chul_no)))

    hits: list[int] = []
    prediction_rows: list[dict[str, Any]] = []
    for race_id in sorted(bucket):
        predicted = [
            chul_no
            for probability, chul_no in sorted(bucket[race_id], reverse=True)[:3]
        ]
        actual = answers.get(race_id, [])[:3]
        hit_count = len(set(predicted) & set(actual))
        hits.append(hit_count)
        prediction_rows.append(
            {
                "race_id": race_id,
                "predicted": predicted,
                "actual": actual,
                "hit_count": hit_count,
            }
        )

    race_count = len(hits)
    return {
        "race_count": race_count,
        "exact_3of3_count": sum(1 for value in hits if value == 3),
        "exact_3of3_rate": (
            sum(1 for value in hits if value == 3) / race_count if race_count else 0.0
        ),
        "avg_set_match": (
            sum(value / 3 for value in hits) / race_count if race_count else 0.0
        ),
        "hit_distribution": {str(value): hits.count(value) for value in range(4)},
        "prediction_rows": prediction_rows,
    }


def _feature_coverage(
    rows: list[dict[str, Any]], features: list[str]
) -> dict[str, Any]:
    row_count = len(rows)
    coverage: dict[str, Any] = {}
    for feature in features:
        present = 0
        for row in rows:
            value = row.get(feature)
            if value is not None and not (isinstance(value, float) and np.isnan(value)):
                present += 1
        coverage[feature] = {
            "present_count": present,
            "missing_count": row_count - present,
            "coverage_rate": present / row_count if row_count else 0.0,
        }
    return coverage


def _gate_report_for_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    payloads = [
        {
            "race_id": record.get("race_id"),
            "standard_payload": record,
            "operational_cutoff_status": record.get("snapshot_meta", {}).get(
                "operational_cutoff_status",
                {},
            ),
            "entry_change_audit": record.get("snapshot_meta", {}).get(
                "entry_change_audit",
                {},
            ),
        }
        for record in records
    ]
    return build_t30_release_gate_report(payloads)


def _evaluate_feature_set(
    *,
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    train_answers: dict[str, list[int]],
    test_answers: dict[str, list[int]],
    features: list[str],
) -> dict[str, Any]:
    x_train, y_train, _train_groups, _train_chuls = _matrix(train_rows, features)
    x_test, _y_test, test_groups, test_chuls = _matrix(test_rows, features)
    model = _make_model()
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    summary = _summarize_predictions(
        groups=test_groups,
        chul_nos=test_chuls,
        probabilities=probabilities,
        answers=test_answers,
    )
    return {
        "feature_count": len(features),
        "features": features,
        "train_row_count": len(train_rows),
        "test_row_count": len(test_rows),
        "train_race_count": len(train_answers),
        "test_race_count": len(test_answers),
        "summary": {
            key: value for key, value in summary.items() if key != "prediction_rows"
        },
        "feature_coverage": _feature_coverage(test_rows, features),
        "prediction_rows": summary["prediction_rows"],
    }


def run_t30_release_evaluation(
    *,
    snapshot_dir: Path = SNAPSHOT_DIR,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    mini = _load_json(snapshot_dir / "mini_val.json")
    holdout = _load_json(snapshot_dir / "holdout.json")
    answer_key = _load_json(snapshot_dir / "answer_key.json")

    baseline_features, removed_config_features = _load_baseline_features(config_path)
    release_features = _release_features(baseline_features)
    mini_rows = _build_rows(mini, answer_key["mini_val"])
    holdout_rows = _build_rows(holdout, answer_key["holdout"])

    baseline = _evaluate_feature_set(
        train_rows=mini_rows,
        test_rows=holdout_rows,
        train_answers=answer_key["mini_val"],
        test_answers=answer_key["holdout"],
        features=baseline_features,
    )
    release = _evaluate_feature_set(
        train_rows=mini_rows,
        test_rows=holdout_rows,
        train_answers=answer_key["mini_val"],
        test_answers=answer_key["holdout"],
        features=release_features,
    )
    baseline_match = baseline["summary"]["avg_set_match"]
    release_match = release["summary"]["avg_set_match"]
    return {
        "format_version": REPORT_VERSION,
        "snapshot_dir": str(snapshot_dir),
        "config_path": str(config_path),
        "removed_config_features": removed_config_features,
        "gate": _gate_report_for_records(holdout),
        "baseline": baseline,
        "release": release,
        "delta": {
            "avg_set_match": release_match - baseline_match,
            "exact_3of3_rate": (
                release["summary"]["exact_3of3_rate"]
                - baseline["summary"]["exact_3of3_rate"]
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", type=Path, default=SNAPSHOT_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_t30_release_evaluation(
        snapshot_dir=args.snapshot_dir,
        config_path=args.config,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
