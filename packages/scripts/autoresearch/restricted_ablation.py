"""Fit one reviewed restricted recipe with API-only and PDF-added feature sets."""

from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from autoresearch.restricted_cohort import (
    API_COLUMNS,
    CONTRACT,
    MAX_MANIFEST_BYTES,
    PDF_FIELDS,
    POLICY,
    ROOT,
    encoded,
    implementation,
    parse_json,
    read_bytes,
    sha256,
    validate_corpus,
    write_new,
)

REVIEW_PATH = ROOT / "data/contracts/restricted_training_review_v1.json"
RECIPE = {
    "feature_contract": CONTRACT,
    "selection_policy": POLICY,
    "solver": "lbfgs",
    "lambda": 1.0,
    "C": "1/training_race_count",
    "sample_weight": "1/observed_roster_size",
    "class_weight": None,
    "fit_intercept": True,
    "tol": 1e-8,
    "max_iter": 2000,
    "random_state": 42,
    "imputation": "train_median_all_missing_zero",
    "scaling": "train_standard",
    "tie_break": "score_desc_gate_asc_canonical_id_asc",
    "train_date": "20261010",
    "development_date": "20261011",
    "evaluation_status": "previously_observed_development_not_forward",
}


@dataclass(frozen=True)
class ReviewedCorpus:
    corpus_bytes: bytes
    review_bytes: bytes
    implementation_bytes: bytes

    def require_unchanged(self) -> None:
        if encoded(implementation()) != self.implementation_bytes:
            raise ValueError("restricted_implementation_changed_after_admission")


def admit(path: Path) -> ReviewedCorpus:
    """Only the repository's exact reviewed bytes authorize this research fit."""
    raw = read_bytes(path, limit=MAX_MANIFEST_BYTES)
    review_raw = read_bytes(REVIEW_PATH, limit=MAX_MANIFEST_BYTES)
    review, corpus = parse_json(review_raw), parse_json(raw)
    current = encoded(implementation())
    if (
        review.get("format_version") != "kra-restricted-review-v1"
        or review.get("purpose") != "research_fit_only"
        or review.get("corpus_sha256") != sha256(raw)
        or review.get("implementation_sha256") != sha256(current)
        or encoded(corpus.get("implementation")) != current
        or review.get("recipe_sha256") != sha256(encoded(RECIPE))
        or review.get("source_review_complete") is not True
        or review.get("label_version_review_complete") is not True
    ):
        raise ValueError("unreviewed_restricted_recipe")
    selected = validate_corpus(corpus)
    if review.get("selected_race_ids") != sorted(r["race_id"] for r in selected):
        raise ValueError("reviewed_membership_mismatch")
    if review.get("selected_runner_count") != sum(
        len(r["feature_rows"]) for r in selected
    ):
        raise ValueError("reviewed_runner_count_mismatch")
    return ReviewedCorpus(raw, review_raw, current)


def columns(arm: str) -> tuple[str, ...]:
    if arm not in ("M0", "M1"):
        raise ValueError("unknown_restricted_arm")
    return (*API_COLUMNS, *PDF_FIELDS) if arm == "M1" else API_COLUMNS


def input_matrix(
    races: list[dict], arm: str
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    values, weights, identities = [], [], []
    for race in sorted(races, key=lambda r: r["race_id"]):
        rows = sorted(race["feature_rows"], key=lambda r: r["chul_no"])
        for row in rows:
            values.append(
                [
                    np.nan if row["features"][k] is None else float(row["features"][k])
                    for k in columns(arm)
                ]
            )
            weights.append(1.0 / len(rows))
            identities.append(
                {
                    "race_id": race["race_id"],
                    "chul_no": row["chul_no"],
                    "horse_id": row["horse_id"],
                }
            )
    return (
        np.asarray(values, dtype=np.float64),
        np.asarray(weights, dtype=np.float64),
        identities,
    )


def matrix(races: list[dict], arm: str) -> tuple:
    values, weights, identities = input_matrix(races, arm)
    answers = {r["race_id"]: set(r["label_top3"]) for r in races}
    labels = np.asarray(
        [int(r["horse_id"] in answers[r["race_id"]]) for r in identities],
        dtype=np.int64,
    )
    return values, labels, weights, identities


def score_model(model: dict, values: np.ndarray) -> np.ndarray:
    if model.get("format_version") != "kra-restricted-logistic-v1" or model[
        "columns"
    ] != list(columns(model["arm"])):
        raise ValueError("invalid_restricted_model")
    filled = np.where(np.isnan(values), np.asarray(model["imputer_statistics"]), values)
    scaled = (filled - np.asarray(model["scaler_mean"])) / np.asarray(
        model["scaler_scale"]
    )
    scores = scaled @ np.asarray(model["coefficients"]) + model["intercept"]
    if not np.isfinite(scores).all():
        raise ValueError("nonfinite_restricted_scores")
    return scores


def predict(model: dict, races: list[dict]) -> list[dict]:
    values, _, identities = input_matrix(races, model["arm"])
    scores = score_model(model, values)
    grouped: dict[str, list] = {}
    for identity, score in zip(identities, scores, strict=True):
        grouped.setdefault(identity["race_id"], []).append((float(score), identity))
    output = []
    for race in sorted(races, key=lambda r: r["race_id"]):
        ranked = sorted(
            grouped[race["race_id"]],
            key=lambda r: (-r[0], r[1]["chul_no"], int(r[1]["horse_id"])),
        )
        selected = [r[1]["horse_id"] for r in ranked[:3]]
        if len(set(selected)) != 3:
            raise ValueError("invalid_exact_three_prediction")
        output.append({"race_id": race["race_id"], "horse_ids": selected})
    return output


def fit(races: list[dict], arm: str) -> tuple[dict, dict]:
    if not races:
        raise ValueError("empty_fit_split")
    values, labels, weights, identities = matrix(races, arm)
    if set(labels.tolist()) != {0, 1}:
        raise ValueError("fit_requires_both_classes")
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    filled = imputer.fit_transform(values)
    scaler = StandardScaler()
    transformed = scaler.fit_transform(filled)
    estimator = LogisticRegression(
        C=1.0 / len(races),
        solver="lbfgs",
        l1_ratio=0,
        tol=RECIPE["tol"],
        max_iter=RECIPE["max_iter"],
        random_state=42,
        class_weight=None,
        fit_intercept=True,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        estimator.fit(transformed, labels, sample_weight=weights)
    if int(estimator.n_iter_.max()) >= RECIPE["max_iter"]:
        raise ValueError("restricted_solver_did_not_converge")
    model = {
        "format_version": "kra-restricted-logistic-v1",
        "arm": arm,
        "columns": list(columns(arm)),
        "recipe": RECIPE,
        "training_race_ids": sorted(r["race_id"] for r in races),
        "C": estimator.C,
        "imputer_statistics": imputer.statistics_.tolist(),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": estimator.coef_[0].tolist(),
        "intercept": float(estimator.intercept_[0]),
        "iterations": int(estimator.n_iter_.max()),
        "model_promoted": False,
    }
    reloaded = parse_json(encoded(model))
    if not np.allclose(
        score_model(reloaded, values),
        estimator.decision_function(transformed),
        rtol=1e-12,
        atol=1e-12,
    ):
        raise ValueError("serialized_model_score_mismatch")
    consumed = {
        "columns": list(columns(arm)),
        "identities": identities,
        "X": transformed.tolist(),
        "y": labels.tolist(),
        "sample_weight": weights.tolist(),
    }
    return model, consumed


def development_report(models: dict, races: list[dict]) -> dict:
    predictions = {arm: predict(model, races) for arm, model in models.items()}
    answers = {r["race_id"]: set(r["label_top3"]) for r in races}
    hits = {
        arm: {r["race_id"]: set(r["horse_ids"]) == answers[r["race_id"]] for r in rows}
        for arm, rows in predictions.items()
    }
    pairs = {"both": 0, "M0_only": 0, "M1_only": 0, "neither": 0}
    for key in answers:
        a, b = hits["M0"][key], hits["M1"][key]
        pairs[
            "both" if a and b else "M0_only" if a else "M1_only" if b else "neither"
        ] += 1
    changed = sum(
        set(a["horse_ids"]) != set(b["horse_ids"])
        for a, b in zip(predictions["M0"], predictions["M1"], strict=True)
    )
    return {
        "status": RECIPE["evaluation_status"],
        "denominator": len(races),
        "exact_hits": {arm: sum(rows.values()) for arm, rows in hits.items()},
        "paired": pairs,
        "changed_combinations": changed,
        "predictions": predictions,
        "counts_as_70_percent_evidence": False,
        "untouched_holdout": False,
        "feature_label_fallback_error_count": 0,
    }


def run(admitted: ReviewedCorpus, directory: Path) -> dict:
    admitted.require_unchanged()
    races = validate_corpus(parse_json(admitted.corpus_bytes))
    train = [r for r in races if r["race_id"].startswith(RECIPE["train_date"] + "_")]
    dev = [
        r for r in races if r["race_id"].startswith(RECIPE["development_date"] + "_")
    ]
    if len(train) + len(dev) != len(races) or not train or not dev:
        raise ValueError("restricted_date_split_mismatch")
    directory.mkdir(parents=True, exist_ok=False)
    pins, development_models = {}, {}
    review = parse_json(admitted.review_bytes)
    for phase, selected in (("development", train), ("full", races)):
        for arm in ("M0", "M1"):
            admitted.require_unchanged()
            model, consumed = fit(selected, arm)
            model.update(
                source_review_id=review["review_id"],
                corpus_sha256=sha256(admitted.corpus_bytes),
                implementation_sha256=sha256(admitted.implementation_bytes),
            )
            matrix_name, model_name = (
                f"{phase}_{arm}_matrix.json",
                f"{phase}_{arm}_model.json",
            )
            pins[matrix_name] = write_new(directory / matrix_name, consumed)
            pins[model_name] = write_new(directory / model_name, model)
            saved = read_bytes(directory / model_name, limit=MAX_MANIFEST_BYTES)
            if sha256(saved) != pins[model_name] or predict(
                parse_json(saved), selected
            ) != predict(model, selected):
                raise ValueError("saved_model_inference_mismatch")
            if phase == "development":
                development_models[arm] = model
    report = development_report(development_models, dev)
    pins["development_report.json"] = write_new(
        directory / "development_report.json", report
    )
    # The receipt is written last: partial artifacts never imply a completed fit.
    admitted.require_unchanged()
    receipt = {
        "format_version": "kra-restricted-fit-receipt-v1",
        "status": "completed",
        "completed_at": datetime.now(UTC).isoformat(),
        "source_review_id": review["review_id"],
        "corpus_sha256": sha256(admitted.corpus_bytes),
        "review_sha256": sha256(admitted.review_bytes),
        "implementation_sha256": sha256(admitted.implementation_bytes),
        "recipe": RECIPE,
        "artifacts": pins,
        "selected_races": len(races),
        "selected_rows": sum(len(r["feature_rows"]) for r in races),
        "model_promoted": False,
        "counts_as_70_percent_evidence": False,
    }
    write_new(directory / "receipt.json", receipt)
    return {
        "receipt_path": str(directory / "receipt.json"),
        "development": report,
        "selected_races": len(races),
        "selected_rows": receipt["selected_rows"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    admitted = admit(args.corpus)
    directory = args.output_dir / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
    )
    print(encoded(run(admitted, directory)).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
