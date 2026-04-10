"""Report schema helpers for evaluation output v2."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from shared.prediction_input_schema import validate_alternative_ranking_dataset_metadata

REQUIRED_TOP_KEYS = {
    "report_version",
    "prompt_version",
    "test_date",
    "total_races",
    "valid_predictions",
    "successful_predictions",
    "success_rate",
    "average_correct_horses",
    "total_correct_horses",
    "avg_execution_time",
    "error_stats",
    "detailed_results",
    "dataset_metadata",
    "feature_schema_version",
    "metrics_v2",
    "leakage_check",
    "promotion_context",
}

REQUIRED_METRIC_KEYS = {
    "log_loss",
    "brier",
    "ece",
    "topk",
    "roi",
    "coverage",
    "deferred_count",
    "samples",
    "prediction_coverage",
    "expected_race_count",
    "predicted_race_count",
    "missing_prediction_count",
    "missing_prediction_race_ids",
    "unexpected_prediction_count",
    "unexpected_prediction_race_ids",
    "json_valid_rate",
    "race_hit_count",
    "race_hit_rate",
    "ordered_race_hit_count",
    "ordered_race_hit_rate",
}


def build_report_v2(
    prompt_version: str,
    summary: dict[str, Any],
    metrics: dict[str, Any],
    leakage: dict[str, Any],
    promotion_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create normalized report payload for v2 while keeping compatibility keys."""

    normalized_summary = {
        "prompt_version": prompt_version,
        "test_date": summary.get("test_date", datetime.now().strftime("%Y%m%d_%H%M%S")),
        "total_races": int(summary.get("total_races", 0)),
        "valid_predictions": int(summary.get("valid_predictions", 0)),
        "successful_predictions": int(summary.get("successful_predictions", 0)),
        "success_rate": float(summary.get("success_rate", 0.0)),
        "average_correct_horses": float(summary.get("average_correct_horses", 0.0)),
        "total_correct_horses": int(summary.get("total_correct_horses", 0)),
        "avg_execution_time": float(summary.get("avg_execution_time", 0.0)),
        "error_stats": summary.get("error_stats", {}),
        "detailed_results": summary.get("detailed_results", []),
        "dataset_metadata": summary.get("dataset_metadata", {}),
        "feature_schema_version": summary.get("feature_schema_version", "unknown"),
    }

    normalized_metrics = {
        "log_loss": float(metrics.get("log_loss", 0.0)),
        "brier": float(metrics.get("brier", 0.0)),
        "ece": float(metrics.get("ece", 0.0)),
        "topk": metrics.get("topk", {}),
        "roi": metrics.get("roi", {}),
        "coverage": float(metrics.get("coverage", 0.0)),
        "deferred_count": int(metrics.get("deferred_count", 0)),
        "samples": int(metrics.get("samples", 0)),
        "prediction_coverage": float(metrics.get("prediction_coverage", 0.0)),
        "expected_race_count": int(metrics.get("expected_race_count", 0)),
        "predicted_race_count": int(metrics.get("predicted_race_count", 0)),
        "missing_prediction_count": int(metrics.get("missing_prediction_count", 0)),
        "missing_prediction_race_ids": [
            str(race_id) for race_id in metrics.get("missing_prediction_race_ids", [])
        ],
        "unexpected_prediction_count": int(
            metrics.get("unexpected_prediction_count", 0)
        ),
        "unexpected_prediction_race_ids": [
            str(race_id)
            for race_id in metrics.get("unexpected_prediction_race_ids", [])
        ],
        "json_valid_rate": float(metrics.get("json_valid_rate", 0.0)),
        "race_hit_count": int(metrics.get("race_hit_count", 0)),
        "race_hit_rate": float(metrics.get("race_hit_rate", 0.0)),
        "ordered_race_hit_count": int(metrics.get("ordered_race_hit_count", 0)),
        "ordered_race_hit_rate": float(metrics.get("ordered_race_hit_rate", 0.0)),
    }

    payload = {
        "report_version": "v2",
        **normalized_summary,
        "metrics_v2": normalized_metrics,
        "leakage_check": leakage,
        "promotion_context": promotion_context or {},
    }

    return payload


def validate_report_v2(report: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate v2 report structure and return errors list."""

    errors: list[str] = []

    missing_top = REQUIRED_TOP_KEYS - set(report.keys())
    if missing_top:
        errors.append(f"missing_top_keys: {sorted(missing_top)}")

    metrics = report.get("metrics_v2", {})
    if not isinstance(metrics, dict):
        errors.append("metrics_v2 must be a dict")
    else:
        missing_metric_keys = REQUIRED_METRIC_KEYS - set(metrics.keys())
        if missing_metric_keys:
            errors.append(f"missing_metric_keys: {sorted(missing_metric_keys)}")

    leakage = report.get("leakage_check", {})
    if not isinstance(leakage, dict):
        errors.append("leakage_check must be a dict")
    else:
        if "passed" not in leakage or "issues" not in leakage:
            errors.append("leakage_check must contain 'passed' and 'issues'")

    dataset_metadata = report.get("dataset_metadata", {})
    if not isinstance(dataset_metadata, dict):
        errors.append("dataset_metadata must be a dict")
    else:
        try:
            normalized_metadata = validate_alternative_ranking_dataset_metadata(
                dataset_metadata
            )
        except ValueError as exc:
            errors.append(str(exc))
        else:
            report["dataset_metadata"] = normalized_metadata
            if (
                report.get("feature_schema_version")
                != normalized_metadata["feature_schema_version"]
            ):
                errors.append(
                    "feature_schema_version must match dataset_metadata.feature_schema_version"
                )

    return len(errors) == 0, errors
