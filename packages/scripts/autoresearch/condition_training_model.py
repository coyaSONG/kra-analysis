"""The fixed PR110 numerical recipe; no approval or implicit refitting here."""

from __future__ import annotations

import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from autoresearch.condition_candidate_inputs import BASE_COLUMNS, COLUMNS
from autoresearch.condition_training_data import LABEL_POLICY, canonical, key
from autoresearch.restricted_cohort import encoded, parse_json

ARMS = {"A24": tuple(BASE_COLUMNS), "B34": tuple(COLUMNS)}
PARAMS = {
    "C": 0.02,
    "solver": "lbfgs",
    "l1_ratio": 0,
    "tol": 1e-8,
    "max_iter": 2000,
    "random_state": 42,
    "class_weight": None,
    "fit_intercept": True,
}
RECIPE = {
    "label_policy": LABEL_POLICY,
    "arms": ARMS,
    "estimator": PARAMS,
    "imputer": {"strategy": "median", "keep_empty_features": True},
    "scaler": "unweighted_StandardScaler",
    "weights": "1/frozen_roster_size",
    "order": "race_id_asc_numeric_gate_asc",
    "selection": "score_desc_numeric_gate_asc_numeric_horse_id_asc",
    "serialization": "three_distinct_canonical_ids_numeric_asc",
    "fit_budget": {"A24": 1, "B34": 1},
    "deterministic_refits": 0,
}


def select(identities, scores):
    if len(identities) != len(scores) or not np.isfinite(scores).all():
        raise ValueError("invalid_scores")
    groups, seen = {}, set()
    for row, score in zip(identities, scores, strict=True):
        identity = key(row["race_id"], row)
        if identity in seen:
            raise ValueError("duplicate_prediction_identity")
        seen.add(identity)
        groups.setdefault(row["race_id"], []).append((float(score), row))
    predictions = []
    for rid, rows in sorted(groups.items()):
        if len(rows) < 3 or len({r[1]["horse_id"] for r in rows}) != len(rows):
            raise ValueError("invalid_prediction_roster")
        ranked = sorted(
            rows, key=lambda r: (-r[0], r[1]["chul_no"], int(r[1]["horse_id"]))
        )
        predictions.append(
            {
                "race_id": rid,
                "horse_ids": canonical([r[1]["horse_id"] for r in ranked[:3]]),
            }
        )
    return predictions


def score(model, x):
    if (
        model.get("format_version") != "condition-logistic-v1"
        or model.get("arm") not in ARMS
    ):
        raise ValueError("invalid_condition_model")
    columns = list(ARMS[model["arm"]])
    if (
        model["columns"] != columns
        or model["classes"] != [0, 1]
        or x.shape[1] != len(columns)
    ):
        raise ValueError("invalid_model_columns_or_classes")
    arrays = {
        k: np.asarray(model[k], dtype=np.float64)
        for k in (
            "imputer_statistics",
            "scaler_mean",
            "scaler_var",
            "scaler_scale",
            "coefficients",
        )
    }
    if any(
        a.shape != (len(columns),) or not np.isfinite(a).all() for a in arrays.values()
    ) or not np.isfinite(model["intercept"]):
        raise ValueError("nonfinite_or_invalid_model")
    if (arrays["scaler_scale"] <= 0).any() or (arrays["scaler_var"] < 0).any():
        raise ValueError("invalid_model_scale")
    filled = np.where(np.isnan(x), arrays["imputer_statistics"], x)
    scaled = (filled - arrays["scaler_mean"]) / arrays["scaler_scale"]
    scores = scaled @ arrays["coefficients"] + model["intercept"]
    if not np.isfinite(scores).all():
        raise ValueError("nonfinite_scores")
    return scores


def fit_once(x, y, weights, identities, arm, before_estimator):
    """Caller must admit the pair before this function performs preprocessing."""
    if arm not in ARMS or x.shape != (len(y), len(ARMS[arm])):
        raise ValueError("invalid_fit_shape")
    imputer = SimpleImputer(**RECIPE["imputer"])
    filled = imputer.fit_transform(x)
    scaler = StandardScaler()
    transformed = scaler.fit_transform(filled)
    estimator = LogisticRegression(**PARAMS)
    actual = estimator.get_params()
    if any(actual[k] != v for k, v in PARAMS.items()):
        raise ValueError("actual_estimator_parameter_mismatch")
    before_estimator(arm)
    with warnings.catch_warnings(record=True) as observed_warnings:
        warnings.simplefilter("always")
        warnings.simplefilter("error", ConvergenceWarning)
        estimator.fit(transformed, y, sample_weight=weights)
    iterations = int(estimator.n_iter_.max())
    if iterations >= PARAMS["max_iter"]:
        raise ValueError("solver_iteration_limit")
    model = {
        "format_version": "condition-logistic-v1",
        "arm": arm,
        "columns": list(ARMS[arm]),
        "classes": estimator.classes_.tolist(),
        "imputer_statistics": imputer.statistics_.tolist(),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_var": scaler.var_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": estimator.coef_[0].tolist(),
        "intercept": float(estimator.intercept_[0]),
        "iterations": iterations,
        "actual_parameters": actual,
        "convergence_warnings": [],
        "warnings": [
            {"category": w.category.__name__, "message": str(w.message)}
            for w in observed_warnings
        ],
        "model_promoted": False,
        "independent_validation_eligible": False,
    }
    reloaded = parse_json(encoded(model))
    saved_scores = score(reloaded, x)
    expected = estimator.decision_function(transformed)
    predictions = select(identities, saved_scores)
    if not np.allclose(
        saved_scores, expected, rtol=0, atol=1e-12
    ) or predictions != select(identities, expected):
        raise ValueError("serialized_score_or_set_mismatch")
    loss = float(np.average(np.logaddexp(0, expected) - y * expected, weights=weights))
    penalty = float(0.5 * np.square(estimator.coef_[0]).sum())
    consumed = {
        "columns": model["columns"],
        "identities": identities,
        "raw_X": [[None if np.isnan(v) else float(v) for v in row] for row in x],
        "X": transformed.tolist(),
        "y": y.tolist(),
        "sample_weight": weights.tolist(),
        "scores": saved_scores.tolist(),
        "predictions": predictions,
        "weighted_mean_log_loss": loss,
        "l2_penalty": penalty,
        "objective": loss + penalty,
        "score_and_exact_set_replay_verified": True,
    }
    return model, consumed
