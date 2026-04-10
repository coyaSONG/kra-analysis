"""시드 단위 평가 지표를 비교 가능한 0..1 스케일로 정규화한다."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from statistics import mean, median, pstdev
from typing import Any, Literal

SEED_METRIC_NORMALIZATION_VERSION = "seed-metric-normalization-v1"
NORMALIZATION_STATUS = Literal["ok", "missing", "abnormal"]
METRIC_DIRECTION = Literal["maximize", "minimize"]

_EPSILON = 1e-9
_MISSING_TEXT_VALUES = frozenset({"", "-", "--", "n/a", "na", "nan", "none", "null"})

DEFAULT_SEED_METRIC_NAMES: tuple[str, ...] = (
    "overall_holdout_hit_rate",
    "overfit_safe_exact_rate",
    "robust_exact_rate",
    "blended_exact_rate",
    "rolling_min_exact_rate",
    "rolling_mean_exact_rate",
    "dev_test_gap",
    "dev_exact_3of3_rate",
    "dev_avg_set_match",
    "test_exact_3of3_rate",
    "test_avg_set_match",
)


@dataclass(frozen=True, slots=True)
class MetricNormalizationRule:
    metric_name: str
    direction: METRIC_DIRECTION
    minimum: float = 0.0
    maximum: float = 1.0
    description: str | None = None


@dataclass(frozen=True, slots=True)
class MetricNormalizationResult:
    metric_name: str
    direction: METRIC_DIRECTION
    raw_value: Any
    normalized_value: float | None
    comparable_value: float | None
    status: NORMALIZATION_STATUS
    issue_code: str | None
    scale_applied: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "direction": self.direction,
            "raw_value": _json_safe_value(self.raw_value),
            "normalized_value": self.normalized_value,
            "comparable_value": self.comparable_value,
            "status": self.status,
            "issue_code": self.issue_code,
            "scale_applied": self.scale_applied,
        }


METRIC_NORMALIZATION_RULES: dict[str, MetricNormalizationRule] = {
    "overall_holdout_hit_rate": MetricNormalizationRule(
        metric_name="overall_holdout_hit_rate",
        direction="maximize",
        description="최근 기간 홀드아웃 최종 판정용 적중률",
    ),
    "overfit_safe_exact_rate": MetricNormalizationRule(
        metric_name="overfit_safe_exact_rate",
        direction="maximize",
        description="과적합 안전 exact 적중률",
    ),
    "robust_exact_rate": MetricNormalizationRule(
        metric_name="robust_exact_rate",
        direction="maximize",
        description="강건 exact 적중률",
    ),
    "blended_exact_rate": MetricNormalizationRule(
        metric_name="blended_exact_rate",
        direction="maximize",
        description="블렌디드 exact 적중률",
    ),
    "rolling_min_exact_rate": MetricNormalizationRule(
        metric_name="rolling_min_exact_rate",
        direction="maximize",
        description="롤링 윈도우 최저 exact 적중률",
    ),
    "rolling_mean_exact_rate": MetricNormalizationRule(
        metric_name="rolling_mean_exact_rate",
        direction="maximize",
        description="롤링 윈도우 평균 exact 적중률",
    ),
    "dev_test_gap": MetricNormalizationRule(
        metric_name="dev_test_gap",
        direction="minimize",
        description="개발/홀드아웃 성능 격차",
    ),
    "dev_exact_3of3_rate": MetricNormalizationRule(
        metric_name="dev_exact_3of3_rate",
        direction="maximize",
        description="개발셋 3두 완전 적중률",
    ),
    "dev_avg_set_match": MetricNormalizationRule(
        metric_name="dev_avg_set_match",
        direction="maximize",
        description="개발셋 평균 set-match",
    ),
    "test_exact_3of3_rate": MetricNormalizationRule(
        metric_name="test_exact_3of3_rate",
        direction="maximize",
        description="홀드아웃 3두 완전 적중률",
    ),
    "test_avg_set_match": MetricNormalizationRule(
        metric_name="test_avg_set_match",
        direction="maximize",
        description="홀드아웃 평균 set-match",
    ),
}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return str(value)
    return str(value)


def _round_unit_interval(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 6)


def _parse_numeric_token(
    value: Any,
) -> tuple[NORMALIZATION_STATUS, float | None, str | None, str | None]:
    if value is None:
        return "missing", None, "missing", None
    if isinstance(value, bool):
        return "abnormal", None, "boolean_not_allowed", None

    percent_suffix = False
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in _MISSING_TEXT_VALUES:
            return "missing", None, "missing", None
        if stripped.endswith("%"):
            percent_suffix = True
            stripped = stripped[:-1].strip()
        stripped = stripped.replace(",", "")
        try:
            numeric = float(stripped)
        except ValueError:
            return "abnormal", None, "non_numeric", None
    else:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "abnormal", None, "unsupported_type", None

    if not math.isfinite(numeric):
        return "abnormal", None, "non_finite", None

    return "ok", numeric, None, "percent_string" if percent_suffix else None


def normalize_metric_value(
    metric_name: str,
    value: Any,
) -> MetricNormalizationResult:
    rule = METRIC_NORMALIZATION_RULES.get(metric_name)
    if rule is None:
        raise KeyError(f"Unsupported metric normalization target: {metric_name}")

    status, parsed_value, issue_code, scale_applied = _parse_numeric_token(value)
    if status != "ok" or parsed_value is None:
        return MetricNormalizationResult(
            metric_name=metric_name,
            direction=rule.direction,
            raw_value=value,
            normalized_value=None,
            comparable_value=None,
            status=status,
            issue_code=issue_code,
            scale_applied=scale_applied,
        )

    scaled_value = parsed_value
    if scale_applied == "percent_string":
        scaled_value = parsed_value / 100.0
    elif abs(parsed_value) > rule.maximum + _EPSILON:
        if abs(parsed_value) <= 100.0 + _EPSILON:
            scaled_value = parsed_value / 100.0
            scale_applied = "percent_numeric"
        else:
            return MetricNormalizationResult(
                metric_name=metric_name,
                direction=rule.direction,
                raw_value=value,
                normalized_value=None,
                comparable_value=None,
                status="abnormal",
                issue_code="out_of_supported_range",
                scale_applied="unsupported_scale",
            )
    else:
        scale_applied = scale_applied or "unit_interval"

    if scaled_value < rule.minimum - _EPSILON or scaled_value > rule.maximum + _EPSILON:
        return MetricNormalizationResult(
            metric_name=metric_name,
            direction=rule.direction,
            raw_value=value,
            normalized_value=None,
            comparable_value=None,
            status="abnormal",
            issue_code="out_of_range",
            scale_applied=scale_applied,
        )

    if rule.maximum <= rule.minimum:
        raise ValueError(f"Invalid normalization range for {metric_name}")

    unit_value = (scaled_value - rule.minimum) / (rule.maximum - rule.minimum)
    unit_value = _round_unit_interval(unit_value)
    comparable_value = (
        unit_value
        if rule.direction == "maximize"
        else _round_unit_interval(1.0 - unit_value)
    )

    return MetricNormalizationResult(
        metric_name=metric_name,
        direction=rule.direction,
        raw_value=value,
        normalized_value=unit_value,
        comparable_value=comparable_value,
        status="ok",
        issue_code=None,
        scale_applied=scale_applied,
    )


def normalize_metric_mapping(
    values: Mapping[str, Any],
    *,
    metric_names: Iterable[str] | None = None,
) -> dict[str, MetricNormalizationResult]:
    selected_names = tuple(metric_names or DEFAULT_SEED_METRIC_NAMES)
    return {
        metric_name: normalize_metric_value(metric_name, values.get(metric_name))
        for metric_name in selected_names
    }


def summarize_normalized_metrics(
    normalized_metrics: Mapping[str, MetricNormalizationResult],
) -> dict[str, Any]:
    ok_count = sum(1 for result in normalized_metrics.values() if result.status == "ok")
    missing_count = sum(
        1 for result in normalized_metrics.values() if result.status == "missing"
    )
    abnormal_count = sum(
        1 for result in normalized_metrics.values() if result.status == "abnormal"
    )
    issue_counts: dict[str, int] = {}
    for result in normalized_metrics.values():
        if result.issue_code is None:
            continue
        issue_counts[result.issue_code] = issue_counts.get(result.issue_code, 0) + 1
    return {
        "schema_version": SEED_METRIC_NORMALIZATION_VERSION,
        "metric_count": len(normalized_metrics),
        "ok_count": ok_count,
        "missing_count": missing_count,
        "abnormal_count": abnormal_count,
        "issue_counts": dict(sorted(issue_counts.items())),
    }


def build_metric_normalization_snapshot(
    values: Mapping[str, Any],
    *,
    metric_names: Iterable[str] | None = None,
) -> dict[str, Any]:
    normalized = normalize_metric_mapping(values, metric_names=metric_names)
    return {
        "schema_version": SEED_METRIC_NORMALIZATION_VERSION,
        "metrics": {
            metric_name: result.to_dict() for metric_name, result in normalized.items()
        },
        "summary": summarize_normalized_metrics(normalized),
    }


def summarize_normalized_metric_rows(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_rows = list(rows)
    normalized_values = [
        float(row["normalized_value"])
        for row in normalized_rows
        if row.get("normalized_value") is not None
    ]
    comparable_values = [
        float(row["comparable_value"])
        for row in normalized_rows
        if row.get("comparable_value") is not None
    ]
    summary: dict[str, Any] = {
        "row_count": len(normalized_rows),
        "ok_count": sum(1 for row in normalized_rows if row.get("status") == "ok"),
        "missing_count": sum(
            1 for row in normalized_rows if row.get("status") == "missing"
        ),
        "abnormal_count": sum(
            1 for row in normalized_rows if row.get("status") == "abnormal"
        ),
    }
    normalized_aggregate = summarize_normalized_seed_metric_values(normalized_values)
    comparable_aggregate = summarize_normalized_seed_metric_values(comparable_values)
    summary.update(
        {
            "normalized_value_aggregate": normalized_aggregate,
            "comparable_value_aggregate": comparable_aggregate,
            # Backward-compatible flat fields retained for existing consumers.
            "normalized_min": normalized_aggregate["min"],
            "normalized_max": normalized_aggregate["max"],
            "normalized_mean": normalized_aggregate["mean"],
            "normalized_stddev": normalized_aggregate["stddev"],
            "normalized_sample_count": normalized_aggregate["sample_count"],
            "comparable_min": comparable_aggregate["min"],
            "comparable_max": comparable_aggregate["max"],
            "comparable_mean": comparable_aggregate["mean"],
            "comparable_stddev": comparable_aggregate["stddev"],
            "comparable_sample_count": comparable_aggregate["sample_count"],
        }
    )
    if comparable_values:
        summary["comparable_median"] = round(median(comparable_values), 6)
    else:
        summary["comparable_median"] = None
    return summary


def summarize_normalized_seed_metric_values(
    values: Iterable[float],
) -> dict[str, Any]:
    numeric_values = [float(value) for value in values]
    if not numeric_values:
        return {
            "sample_count": 0,
            "mean": None,
            "stddev": None,
            "min": None,
            "max": None,
        }

    return {
        "sample_count": len(numeric_values),
        "mean": round(mean(numeric_values), 6),
        "stddev": round(pstdev(numeric_values), 6),
        "min": round(min(numeric_values), 6),
        "max": round(max(numeric_values), 6),
    }
