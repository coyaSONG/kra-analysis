"""시드별 성능 row 를 표준화하고 편차/이상치 판단용 집계를 계산한다."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from statistics import mean, median, pstdev
from typing import Any

from shared.seed_metric_normalization import (
    METRIC_NORMALIZATION_RULES,
    normalize_metric_value,
)

SEED_PERFORMANCE_ROW_VERSION = "seed-performance-row-v1"
SEED_PERFORMANCE_AGGREGATION_VERSION = "seed-performance-aggregation-v1"
DEFAULT_QUANTILES: tuple[float, ...] = (0.1, 0.25, 0.5, 0.75, 0.9)
DEFAULT_OUTLIER_IQR_MULTIPLIER = 1.5

_RUN_ID_KEYS: tuple[str, ...] = ("run_id", "runId")
_SEED_INDEX_KEYS: tuple[str, ...] = ("seed_index", "seedIndex")
_MODEL_RANDOM_STATE_KEYS: tuple[str, ...] = (
    "model_random_state",
    "modelRandomState",
    "seed",
    "random_state",
)
_STATUS_KEYS: tuple[str, ...] = ("status",)


def _first_present(payload: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _int_or_none(value: Any) -> int | None:
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    if probability <= 0.0:
        return values[0]
    if probability >= 1.0:
        return values[-1]
    position = (len(values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return values[lower_index]
    fraction = position - lower_index
    lower_value = values[lower_index]
    upper_value = values[upper_index]
    return lower_value + (upper_value - lower_value) * fraction


def summarize_seed_metric_distribution(
    values: Iterable[float],
    *,
    quantiles: Iterable[float] = DEFAULT_QUANTILES,
    outlier_iqr_multiplier: float = DEFAULT_OUTLIER_IQR_MULTIPLIER,
) -> dict[str, Any]:
    numeric_values = sorted(float(value) for value in values)
    if not numeric_values:
        return {
            "sample_count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "stddev": None,
            "quantiles": {},
            "iqr": None,
            "lower_fence": None,
            "upper_fence": None,
        }

    quantile_map = {
        f"p{int(probability * 100):02d}": round(
            _quantile(numeric_values, float(probability)),
            6,
        )
        for probability in quantiles
    }
    q1 = quantile_map.get("p25")
    q3 = quantile_map.get("p75")
    iqr = round(q3 - q1, 6) if q1 is not None and q3 is not None else None
    lower_fence = (
        round(q1 - (outlier_iqr_multiplier * iqr), 6)
        if q1 is not None and iqr is not None
        else None
    )
    upper_fence = (
        round(q3 + (outlier_iqr_multiplier * iqr), 6)
        if q3 is not None and iqr is not None
        else None
    )
    return {
        "sample_count": len(numeric_values),
        "min": round(min(numeric_values), 6),
        "max": round(max(numeric_values), 6),
        "mean": round(mean(numeric_values), 6),
        "median": round(median(numeric_values), 6),
        "stddev": round(pstdev(numeric_values), 6),
        "quantiles": quantile_map,
        "iqr": iqr,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
    }


def standardize_seed_metric_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    metric_name: str,
    value_source_key: str | None = None,
) -> list[dict[str, Any]]:
    standardized_rows: list[dict[str, Any]] = []
    for row in rows:
        run_id = _first_present(row, _RUN_ID_KEYS)
        if run_id in ("", None):
            raise ValueError(f"{metric_name} aggregation row requires run_id")
        result = normalize_metric_value(metric_name, row.get(metric_name))
        standardized_rows.append(
            {
                "format_version": SEED_PERFORMANCE_ROW_VERSION,
                "metric_name": metric_name,
                "run_id": str(run_id),
                "seed_index": _int_or_none(_first_present(row, _SEED_INDEX_KEYS)),
                "model_random_state": _int_or_none(
                    _first_present(row, _MODEL_RANDOM_STATE_KEYS)
                ),
                "run_status": str(_first_present(row, _STATUS_KEYS) or "unknown"),
                "value_source": (
                    row.get(value_source_key) if value_source_key is not None else None
                ),
                **result.to_dict(),
            }
        )
    standardized_rows.sort(
        key=lambda item: (
            item["seed_index"] if item["seed_index"] is not None else 10**9,
            item["run_id"],
        )
    )
    return standardized_rows


def _classify_outlier(
    value: float | None,
    *,
    lower_fence: float | None,
    upper_fence: float | None,
) -> str | None:
    if value is None or lower_fence is None or upper_fence is None:
        return None
    if value < lower_fence:
        return "low"
    if value > upper_fence:
        return "high"
    return None


def build_seed_metric_aggregate(
    rows: Iterable[Mapping[str, Any]],
    *,
    metric_name: str,
    value_source_key: str | None = None,
    quantiles: Iterable[float] = DEFAULT_QUANTILES,
    outlier_iqr_multiplier: float = DEFAULT_OUTLIER_IQR_MULTIPLIER,
) -> dict[str, Any]:
    standardized_rows = standardize_seed_metric_rows(
        rows,
        metric_name=metric_name,
        value_source_key=value_source_key,
    )
    normalized_summary = summarize_seed_metric_distribution(
        (
            float(row["normalized_value"])
            for row in standardized_rows
            if row["normalized_value"] is not None
        ),
        quantiles=quantiles,
        outlier_iqr_multiplier=outlier_iqr_multiplier,
    )
    comparable_summary = summarize_seed_metric_distribution(
        (
            float(row["comparable_value"])
            for row in standardized_rows
            if row["comparable_value"] is not None
        ),
        quantiles=quantiles,
        outlier_iqr_multiplier=outlier_iqr_multiplier,
    )
    outlier_basis = (
        "comparable_value"
        if comparable_summary["sample_count"] > 0
        else "normalized_value"
    )
    outlier_summary = (
        comparable_summary
        if outlier_basis == "comparable_value"
        else normalized_summary
    )
    low_outlier_run_ids: list[str] = []
    high_outlier_run_ids: list[str] = []
    enriched_rows: list[dict[str, Any]] = []
    for row in standardized_rows:
        outlier_value = row.get(outlier_basis)
        outlier_label = _classify_outlier(
            float(outlier_value) if outlier_value is not None else None,
            lower_fence=outlier_summary["lower_fence"],
            upper_fence=outlier_summary["upper_fence"],
        )
        if outlier_label == "low":
            low_outlier_run_ids.append(row["run_id"])
        elif outlier_label == "high":
            high_outlier_run_ids.append(row["run_id"])
        enriched_row = dict(row)
        enriched_row["outlier_basis"] = outlier_basis
        enriched_row["outlier_label"] = outlier_label
        enriched_rows.append(enriched_row)

    rule = METRIC_NORMALIZATION_RULES[metric_name]
    summary = {
        "row_count": len(enriched_rows),
        "ok_count": sum(1 for row in enriched_rows if row["status"] == "ok"),
        "missing_count": sum(1 for row in enriched_rows if row["status"] == "missing"),
        "abnormal_count": sum(
            1 for row in enriched_rows if row["status"] == "abnormal"
        ),
        "normalized_value_aggregate": normalized_summary,
        "comparable_value_aggregate": comparable_summary,
        "outlier_analysis": {
            "basis": outlier_basis,
            "strategy": "iqr",
            "iqr_multiplier": outlier_iqr_multiplier,
            "sample_count": outlier_summary["sample_count"],
            "q1": outlier_summary["quantiles"].get("p25"),
            "q3": outlier_summary["quantiles"].get("p75"),
            "iqr": outlier_summary["iqr"],
            "lower_fence": outlier_summary["lower_fence"],
            "upper_fence": outlier_summary["upper_fence"],
            "low_outlier_count": len(low_outlier_run_ids),
            "high_outlier_count": len(high_outlier_run_ids),
            "outlier_run_ids": tuple(low_outlier_run_ids + high_outlier_run_ids),
            "low_outlier_run_ids": tuple(low_outlier_run_ids),
            "high_outlier_run_ids": tuple(high_outlier_run_ids),
        },
        # Existing report/tests consume these flat aliases.
        "normalized_min": normalized_summary["min"],
        "normalized_max": normalized_summary["max"],
        "normalized_mean": normalized_summary["mean"],
        "normalized_median": normalized_summary["median"],
        "normalized_stddev": normalized_summary["stddev"],
        "normalized_sample_count": normalized_summary["sample_count"],
        "comparable_min": comparable_summary["min"],
        "comparable_max": comparable_summary["max"],
        "comparable_mean": comparable_summary["mean"],
        "comparable_median": comparable_summary["median"],
        "comparable_stddev": comparable_summary["stddev"],
        "comparable_sample_count": comparable_summary["sample_count"],
    }
    return {
        "schema_version": SEED_PERFORMANCE_AGGREGATION_VERSION,
        "row_format_version": SEED_PERFORMANCE_ROW_VERSION,
        "metric_name": metric_name,
        "rule": {
            "metric_name": metric_name,
            "direction": rule.direction,
            "description": rule.description,
        },
        "summary": summary,
        "rows": enriched_rows,
    }
