from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.seed_metric_normalization import (  # noqa: E402
    build_metric_normalization_snapshot,
    normalize_metric_value,
    summarize_normalized_metric_rows,
    summarize_normalized_seed_metric_values,
)


def test_normalize_metric_value_accepts_ratio_percent_string_and_percent_numeric() -> (
    None
):
    ratio = normalize_metric_value("overall_holdout_hit_rate", 0.71)
    percent_string = normalize_metric_value("overall_holdout_hit_rate", "71%")
    percent_numeric = normalize_metric_value("overall_holdout_hit_rate", 71)

    assert ratio.normalized_value == 0.71
    assert percent_string.normalized_value == 0.71
    assert percent_numeric.normalized_value == 0.71
    assert percent_string.scale_applied == "percent_string"
    assert percent_numeric.scale_applied == "percent_numeric"


def test_normalize_metric_value_inverts_minimize_direction_for_comparison() -> None:
    gap = normalize_metric_value("dev_test_gap", "12%")

    assert gap.normalized_value == 0.12
    assert gap.comparable_value == 0.88
    assert gap.direction == "minimize"
    assert gap.status == "ok"


def test_normalize_metric_value_distinguishes_missing_and_abnormal_inputs() -> None:
    missing = normalize_metric_value("robust_exact_rate", None)
    abnormal = normalize_metric_value("robust_exact_rate", "seventy")
    overscaled = normalize_metric_value("robust_exact_rate", 170)

    assert missing.status == "missing"
    assert missing.issue_code == "missing"
    assert abnormal.status == "abnormal"
    assert abnormal.issue_code == "non_numeric"
    assert overscaled.status == "abnormal"
    assert overscaled.issue_code == "out_of_supported_range"


def test_build_metric_normalization_snapshot_summarizes_issue_counts() -> None:
    snapshot = build_metric_normalization_snapshot(
        {
            "overall_holdout_hit_rate": "71%",
            "overfit_safe_exact_rate": None,
            "robust_exact_rate": "invalid",
        },
        metric_names=(
            "overall_holdout_hit_rate",
            "overfit_safe_exact_rate",
            "robust_exact_rate",
        ),
    )

    assert snapshot["summary"]["ok_count"] == 1
    assert snapshot["summary"]["missing_count"] == 1
    assert snapshot["summary"]["abnormal_count"] == 1
    assert snapshot["summary"]["issue_counts"] == {
        "missing": 1,
        "non_numeric": 1,
    }
    assert snapshot["metrics"]["overall_holdout_hit_rate"]["normalized_value"] == 0.71


def test_summarize_normalized_seed_metric_values_returns_dispersion_stats() -> None:
    summary = summarize_normalized_seed_metric_values([0.2, 0.4, 0.6])

    assert summary == {
        "sample_count": 3,
        "mean": 0.4,
        "stddev": 0.163299,
        "min": 0.2,
        "max": 0.6,
    }


def test_summarize_normalized_metric_rows_exposes_normalized_and_comparable_aggregates() -> (
    None
):
    summary = summarize_normalized_metric_rows(
        [
            normalize_metric_value("overall_holdout_hit_rate", "40%").to_dict(),
            normalize_metric_value("overall_holdout_hit_rate", 0.7).to_dict(),
            normalize_metric_value("overall_holdout_hit_rate", None).to_dict(),
        ]
    )

    assert summary["row_count"] == 3
    assert summary["ok_count"] == 2
    assert summary["missing_count"] == 1
    assert summary["normalized_value_aggregate"] == {
        "sample_count": 2,
        "mean": 0.55,
        "stddev": 0.15,
        "min": 0.4,
        "max": 0.7,
    }
    assert summary["comparable_value_aggregate"] == {
        "sample_count": 2,
        "mean": 0.55,
        "stddev": 0.15,
        "min": 0.4,
        "max": 0.7,
    }
    assert summary["normalized_sample_count"] == 2
    assert summary["comparable_sample_count"] == 2
    assert summary["comparable_median"] == 0.55
